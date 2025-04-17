import csv
import sys
import os
from os.path import isfile
import logging
from unstructured.partition.pdf import partition_pdf
from pypdf import PdfReader, PdfWriter


class PDFToConverter:
    def __init__(self, target_folder):
        self.target_folder = target_folder
        self.file_list = self.get_pdf_files()
        self.split_size = 10  # 分割数

    def _mkdir_folder(self, folder_name: str):
        output_folder = os.path.join(self.target_folder, folder_name)
        os.makedirs(output_folder, exist_ok=True)
        return output_folder

    def get_basename(self, file_number: int):
        return os.path.splitext(os.path.basename(self.file_list[file_number]))[0]

    def get_pdf_files(self, target_folder_name: str = None):
        if target_folder_name is None:
            folder_path = self.target_folder
        else:
            folder_path = os.path.join(self.target_folder, target_folder_name)

        file_list = [f for f in os.listdir(folder_path) if
                     os.path.isfile(os.path.join(folder_path, f)) and f.endswith('.pdf')]
        return file_list

    def split_pdf(self, file_number: int):
        base_name = self.get_basename(file_number=file_number)
        save_folder = self._mkdir_folder(folder_name=base_name)
        reader = PdfReader(os.path.join(self.target_folder, self.file_list[file_number]))
        total_pages = len(reader.pages)

        for i in range(0, total_pages, self.split_size):
            writer = PdfWriter()
            for j in range(i, min(i + self.split_size, total_pages)):
                writer.add_page(reader.pages[j])

            output_file_path = os.path.join(save_folder, f"{base_name}_{i // self.split_size + 1}.pdf")
            with open(output_file_path, "wb") as output_file:
                writer.write(output_file)

        print(f"PDFファイル分割完了: {base_name}")

    def pdf_to_string(self, file_number: int):
        base_name = self.get_basename(file_number=file_number)
        output_path = os.path.join(self.target_folder, f"{base_name}.csv")

        # すでにCSVファイルがある場合はスキップ
        if isfile(output_path):
            return

        logging.getLogger("pdfminer").setLevel(logging.ERROR)  # 警告メッセージの抑止

        file_list = self.get_pdf_files(base_name)
        export_list = []

        for i in range(len(file_list)):  # ファイルごと
            target_file = os.path.join(self.target_folder, base_name, file_list[i])
            reader = PdfReader(stream=target_file)
            for j in range(len(reader.pages)):  # ページごと
                elements = partition_pdf(filename=target_file)
                text_elements = [el.text for el in elements if hasattr(el, "text") and el.text]
                for k in range(len(text_elements)):
                    export_list.append({"page": i + 1, "内容": text_elements[k]})

        self.export_csv(export_file_path=output_path, export_data=export_list)

    @staticmethod
    def export_csv(export_file_path: str, export_data: list[dict[str, str]]):
        with open(file=export_file_path, mode="w", encoding='UTF-8', newline="") as f:
            field_names = ['page', '内容']
            writer = csv.DictWriter(f=f, fieldnames=field_names, quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writerows(export_data)


def main():
    if len(sys.argv) == 1:
        folder_path = input("フォルダパス：").replace('"', '')
    else:
        folder_path = sys.argv[1]

    pdf_convert = PDFToConverter(target_folder=folder_path)

    for i in range(len(pdf_convert.file_list)):
        pdf_convert.split_pdf(file_number=i)
        pdf_convert.pdf_to_string(file_number=i)
        print(f"完了：{pdf_convert.file_list[i]}")


if __name__ == '__main__':
    main()
