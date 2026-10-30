"""Create a research-only dataset copy with unprovisioned synthetic credentials."""

import argparse
import json
import random
import re
import shutil
import string
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER = re.compile(rb"__SYNTHETIC_[A-Za-z0-9_]+__")


def generate_credentials(seed=None):
    rng = random.SystemRandom() if seed is None else random.Random(seed)
    alphanumeric = string.ascii_letters + string.digits
    urlsafe = alphanumeric + "_-"

    def text(alphabet, length):
        return "".join(rng.choice(alphabet) for _ in range(length))

    def google_client_id():
        return (
            text(string.digits, 12) + "-" + text(string.ascii_lowercase + string.digits, 32)
            + ".apps.googleusercontent.com"
        )

    values = {
        "OPENWEATHER_API_KEY": text("0123456789abcdef", 32),
        "QPAY_STRIPE_SECRET_KEY": "sk_test_" + text(alphanumeric, 24),
        "QPAY_STRIPE_PUBLISHABLE_KEY": "pk_test_" + text(alphanumeric, 24),
        "DANCE_GOOGLE_CLIENT_ID": google_client_id(),
        "DANCE_GOOGLE_CLIENT_SECRET": text(urlsafe, 24),
        "BUILDUP_GOOGLE_CLIENT_ID": google_client_id(),
        "BUILDUP_GOOGLE_CLIENT_SECRET": text(urlsafe, 24),
        "PROYECTO_STRIPE_SECRET_KEY": "sk_test_" + text(alphanumeric, 24) + "00" + text(alphanumeric, 8),
        "PROYECTO_STRIPE_PUBLISHABLE_KEY": "pk_test_" + text(alphanumeric, 24) + "00" + text(alphanumeric, 8),
        "OCR_MONGODB_URI": (
            "mongodb+srv://research_" + text(alphanumeric, 12) + ":" + text(alphanumeric, 24)
            + "@cluster-" + text(string.ascii_lowercase + string.digits, 10)
            + ".example.invalid/OCRHack?retryWrites=true&w=majority"
        ),
        "OCR_FLASK_SECRET_KEY": text(alphanumeric, 10),
    }
    return {"__SYNTHETIC_" + name + "__": value for name, value in values.items()}


def generate_dataset(source, destination, seed=None):
    source = Path(source).resolve(strict=True)
    destination = Path(destination).resolve()
    if not source.is_dir():
        raise ValueError("The source dataset must be a directory.")
    if source == destination or source in destination.parents or destination in source.parents:
        raise ValueError("Source and destination must not overlap.")
    if destination.exists():
        raise FileExistsError("Output already exists; choose a new output directory.")
    if any(path.is_symlink() for path in source.rglob("*")):
        raise ValueError("The source dataset must not contain symbolic links.")

    values = generate_credentials(seed)
    replacements = {key.encode("ascii"): value.encode("ascii") for key, value in values.items()}
    counts = dict.fromkeys(values, 0)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".synthetic-", dir=destination.parent) as temporary:
        staging = Path(temporary) / "dataset"
        shutil.copytree(source, staging / "examples")
        for path in sorted((staging / "examples").rglob("*")):
            if not path.is_file():
                continue
            data = path.read_bytes()

            def replace(match):
                placeholder = match.group()
                if placeholder not in replacements:
                    raise ValueError("Unknown placeholder: " + placeholder.decode("ascii"))
                counts[placeholder.decode("ascii")] += 1
                return replacements[placeholder]

            updated = PLACEHOLDER.sub(replace, data)
            if updated != data:
                path.write_bytes(updated)
        missing = [key for key, count in counts.items() if not count]
        if missing:
            raise ValueError("Missing expected placeholders: " + ", ".join(missing))
        (staging / "synthetic-credentials.json").write_text(
            json.dumps(
                {"synthetic": True, "seed": seed, "values": values, "occurrences": counts},
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )
        staging.rename(destination)
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / ".synthetic-dataset",
        help="New output directory (default: the ignored .synthetic-dataset in this checkout).",
    )
    parser.add_argument("--seed", type=int, help="Optional seed for reproducible research fixtures.")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    ignored = ROOT / ".synthetic-dataset"
    if ROOT in output.parents and output != ignored and ignored not in output.parents:
        parser.error("Use .synthetic-dataset or a directory outside the checkout to avoid committing synthetic keys.")
    try:
        counts = generate_dataset(ROOT / "examples", output, args.seed)
    except (OSError, ValueError, shutil.Error) as error:
        parser.exit(1, f"Generation failed: {error}\n")
    print(f"Generated {sum(counts.values())} synthetic substitutions in {output}")
    print("Research fixtures only: these credentials are not provisioned with any service. Do not commit them.")


if __name__ == "__main__":
    main()
