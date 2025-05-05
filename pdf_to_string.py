import csv
import sys
import os
import logging
from unstructured.partition.pdf import partition_pdf
from pypdf import PdfReader, PdfWriter
import functools
from ja_sentence_segmenter.common.pipeline import make_pipeline
from ja_sentence_segmenter.concatenate.simple_concatenator import concatenate_matching
from ja_sentence_segmenter.normalize.neologd_normalizer import normalize
from ja_sentence_segmenter.split.simple_splitter import split_newline, split_punctuation


class PDFToConverter:
    def __init__(self, target_folder, output_type=1):
        self.target_folder = target_folder
        self.file_list = self.get_pdf_files()
        self.split_size = 10  # 分割数
        self.row_count = 1  # 行数カウント
        self.output_type = output_type  # 出力形式

    def _mkdir_folder(self, folder_name: str):
        output_folder = os.path.join(self.target_folder, folder_name)
        os.makedirs(output_folder, exist_ok=True)
        return output_folder

    def get_basename(self, file_number: int):
        return os.path.splitext(os.path.basename(self.file_list[file_number]))[0]

    def get_output_path(self, base_name: str = None):
        if self.output_type == 1:  # CSV形式（行数、カテゴリ、内容を出力）
            return os.path.join(self.target_folder, f"{base_name}.csv")
        elif self.output_type == 2:  # txt（内容のみ・区切り未処理）
            return os.path.join(self.target_folder, f"{base_name}.txt")
        else:  # txt（内容のみ・区切り処理）
            return os.path.join(self.target_folder, f"{base_name}_processed.txt")

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
        output_path = self.get_output_path(base_name=base_name)

        # すでに出力ファイルがある場合は削除
        if os.path.isfile(output_path):
            os.remove(output_path)

        logging.getLogger("pdfminer").setLevel(logging.ERROR)  # 警告メッセージの抑止

        file_list = self.get_pdf_files(base_name)
        export_list = []

        for i in range(len(file_list)):  # ファイルごと
            target_file = os.path.join(self.target_folder, base_name, file_list[i])
            elements = partition_pdf(filename=target_file)
            for j in range(len(elements)):
                export_list.append(
                    {
                        "行数": self.row_count,
                        "カテゴリ": elements[j].category,
                        "内容": elements[j].text,
                    }
                )
                self.row_count += 1

        self.export_to_file(output_path=output_path, export_list=export_list)

    @staticmethod
    def japanese_text_process(export_list: list):
        split_punc2 = functools.partial(split_punctuation, punctuations=r"。!?")
        concat_tail_no = functools.partial(
            concatenate_matching,
            former_matching_rule=r"^(?P<result>.+)(の)$",
            remove_former_matched=False)
        segmenter = make_pipeline(normalize, split_newline, concat_tail_no, split_punc2)
        segments = list(segmenter("".join([export_list[i]["内容"] for i in range(len(export_list))])))
        return segments

    def export_to_file(self, output_path: str, export_list: list):
        if self.output_type == 1:  # 1:CSV（行数、カテゴリ、内容を出力）
            with open(output_path, "a", encoding="utf-8") as output_file:
                writer = csv.DictWriter(
                    output_file,
                    ["行数", "カテゴリ", "内容"],
                    quoting=csv.QUOTE_ALL,
                    delimiter=",",
                    lineterminator="\n")
                writer.writeheader()
                for i in range(len(export_list)):
                    writer.writerow(export_list[i])

        elif self.output_type == 2:  # txt（内容のみ・区切り未処理）
            with open(output_path, "a", encoding="utf-8") as output_file:
                output_file.write("\n".join([export_list[i]["内容"] for i in range(len(export_list))]))

        else:  # txt（内容のみ・区切り処理）
            with open(output_path, "a", encoding="utf-8") as output_file:
                # output_file.write("\n".join(self.japanese_text_process(export_list=export_list) + ["\n"] * 2))
                output_file.write("\n".join(self.japanese_text_process(export_list=export_list)))


def check_path_type(path):
    if not os.path.exists(path):
        print(f"パスが存在しません: {path}")
        sys.exit()

    if os.path.isfile(path):
        if path.lower().endswith('.pdf'):
            return "file"
        else:
            print(f"対象のファイルはPDFではありません: {path}")
            sys.exit()
    elif os.path.isdir(path):
        return "folder"
    else:
        print(f"不明なパスです: {path}")
        sys.exit()


def get_output_type():
    while True:
        print("\n出力形式を選択してください：")
        print("1: CSV（行数、カテゴリ、内容を出力）")
        print("2: txt（内容のみ・区切り未処理）")
        print("3: txt（内容のみ・区切り処理）")

        try:
            output_type = int(input("選択 (1-3): "))
            if 1 <= output_type <= 3:
                return output_type
            else:
                print("エラー：1から3の数字を入力してください。")
        except ValueError:
            print("エラー：数字を入力してください。")


def main():
    if len(sys.argv) == 1:
        path = input("パスを入力してください：").replace('"', '').strip()
        output_type = get_output_type()
    else:
        path = sys.argv[1]
        output_type = int(sys.argv[2]) if len(sys.argv) == 3 else 1

    path_type = check_path_type(path)

    if path_type == "folder":
        pdf_convert = PDFToConverter(target_folder=path, output_type=output_type)
        for i in range(len(pdf_convert.file_list)):
            pdf_convert.split_pdf(file_number=i)
            pdf_convert.pdf_to_string(file_number=i)
            print(f"完了：{pdf_convert.file_list[i]}")
    elif path_type == "file":
        # 単一PDFファイルを処理
        pdf_convert = PDFToConverter(target_folder=os.path.dirname(path), output_type=output_type)
        for i in range(len(pdf_convert.file_list)):
            if os.path.basename(path) == pdf_convert.file_list[i]:
                pdf_convert.split_pdf(file_number=i)
                pdf_convert.pdf_to_string(file_number=i)
        print(f"完了：{os.path.basename(path)}")


if __name__ == '__main__':
    main()
