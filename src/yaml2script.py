import csv
import sys
import typing as t

import yaml


def main(input_path: str):
    with open(input_path, "r") as f:
        lines = yaml.safe_load(f)

    writer = csv.writer(sys.stdout)
    for line in lines:
        if isinstance(line, str):
            continue
        if isinstance(line, dict):
            if "image" in line or "text" in line:
                continue
            assert len(line) == 1
            name, message = list(line.items())[0]
            writer.writerow([name, message.strip()])


if __name__ == "__main__":
    main(sys.argv[1])
