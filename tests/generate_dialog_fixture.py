"""Create synthetic CP949 dialogue for CI without distributing game text."""
from pathlib import Path
import sys


def main(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    korean = (
        "안녕하세요. 이 문장은 테스트용으로 작성한 한국어 대화입니다. "
        "한글과 English 단어를 섞어 길이를 다양하게 만들어 문자 경계를 검사합니다. "
    )
    for file_no in range(4):
        lines = []
        for number in range(80):
            n = file_no * 80 + number
            # Mix short choices with long NPC replies, no line endings in a record.
            text = (
                "이야기를 계속한다." if n % 7 == 0
                else (korean * (1 + n % 4)) + f"검사 항목 {n} / 선택지 {n % 8}"
            )
            lines.append(f"{{{100+n}}}{{}}{{{text}}}")
        (folder / f"synthetic-{file_no}.msg").write_bytes(
            ("\r\n".join(lines) + "\r\n").encode("cp949")
        )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: generate_dialog_fixture.py <output-folder>")
    main(Path(sys.argv[1]))
