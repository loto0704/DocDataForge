import os.path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from pathlib import Path
import json


class TextChunker:
    def __init__(self, chunk_size=1000, chunk_overlap=200):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )

    def chunk_text_from_file(self, file_path: str) -> list:
        """
        ファイルからテキストを読み込み、チャンクに分割します。
        Args:
            file_path (str): 入力テキストファイルのパス
        Returns:
            list: 分割されたテキストチャンクのリスト
        """
        # ファイルを読み込み
        try:
            text = Path(file_path).read_text(encoding='utf-8')
            text = text.replace(" ", "") # 無駄なスペースを削除
            # テキストをチャンクに分割
            chunks = self.text_splitter.split_text(text)
            return chunks
        except Exception as e:
            print(f"エラーが発生しました: {e}")
            return []

    @staticmethod
    def save_chunks_to_file(chunks: list, output_path: str, format: str = 'txt') -> bool:
        """
        チャンクをファイルに保存します。
        Args:
            chunks (list): 保存するテキストチャンクのリスト
            output_path (str): 出力ファイルのパス
            format (str): 出力フォーマット（'txt' または 'json'）
        Returns:
            bool: 保存が成功したかどうか
        """
        try:
            if format.lower() == 'txt':
                with Path(output_path).open('w', encoding='utf-8') as f:
                    for i, chunk in enumerate(chunks, 1):
                        f.write(f"チャンク {i}:\n")
                        f.write(chunk)
                        f.write('\n' + '-' * 50 + '\n')
            elif format.lower() == 'json':
                chunk_dict = {f"chunk_{i}": chunk for i, chunk in enumerate(chunks, 1)}
                with Path(output_path).open('w', encoding='utf-8') as f:
                    json.dump(chunk_dict, f, ensure_ascii=False, indent=2)
            else:
                print(f"未対応のフォーマットです: {format}")
                return False
            return True
        except Exception as e:
            print(f"保存中にエラーが発生しました: {e}")
            return False


def main():
    chunker = TextChunker()
    
    # ファイルの読み込みと分割
    input_path = input("入力ファイルパス：").replace('"', '')
    chunks = chunker.chunk_text_from_file(input_path)
    
    if not chunks:
        print("チャンクの生成に失敗しました。")
        return
    
    # 保存するかどうかの確認
    save_option = input("チャンクを保存しますか？ (y/n): ").lower()
    if save_option == 'y':
        output_format = input("保存フォーマットを選択してください（txt/json）: ").lower()
        output_dir = os.path.dirname(input_path)
        output_file_name = os.path.splitext(os.path.basename(input_path))[0] + f"_chunks.{output_format}"
        output_path = os.path.join(output_dir, output_file_name)
        
        if chunker.save_chunks_to_file(chunks, output_path, output_format):
            print(f"チャンクを {output_path} に保存しました。")
        else:
            print("チャンクの保存に失敗しました。")
    
    # チャンクの表示
    display_option = input("チャンクを表示しますか？ (y/n): ").lower()
    if display_option == 'y':
        for i, chunk in enumerate(chunks, 1):
            print(f"チャンク {i}:")
            print(chunk)
            print("-" * 50)


if __name__ == "__main__":
    main()