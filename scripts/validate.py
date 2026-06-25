import json
import sys
from pathlib import Path

from jsonschema.validators import validator_for
from referencing import Registry, Resource


def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def build_registry(schemas_dir):
    """Register every JSON document under schemas/ that declares an ``$id``.

    This lets cross-file ``$ref``s (e.g. a journal article referencing the
    shared citation schema) resolve against an in-memory registry instead of
    trying to fetch the ``$id`` URI over the network.
    """
    resources = []
    for path in schemas_dir.rglob("*.json"):
        doc = load_json(path)
        if isinstance(doc, dict) and "$id" in doc:
            resources.append((doc["$id"], Resource.from_contents(doc)))
    return Registry().with_resources(resources)


def main():
    root_dir = Path(__file__).parent.parent
    schemas_dir = root_dir / "schemas"

    registry = build_registry(schemas_dir)
    success = True

    # Find all schema.json files
    for schema_path in schemas_dir.rglob("schema.json"):
        print(f"\nEvaluating schema: {schema_path.relative_to(root_dir)}")
        schema = load_json(schema_path)
        # Pick the validator class declared by the schema's "$schema" (e.g.
        # draft-07 for the Aquinas corpus, 2020-12 for the journal article).
        validator_cls = validator_for(schema)
        validator_cls.check_schema(schema)
        validator = validator_cls(schema, registry=registry)

        # Check corresponding examples folder
        examples_dir = schema_path.parent / "examples"
        if not examples_dir.exists():
            print(f"  [WARN] No examples directory found for {schema_path.parent.name}")
            continue

        for example_path in sorted(examples_dir.glob("*.json")):
            instance = load_json(example_path)
            errors = sorted(validator.iter_errors(instance), key=lambda e: e.path)

            if not errors:
                print(f"  [PASS] {example_path.name}")
            else:
                success = False
                print(f"  [FAIL] {example_path.name}")
                for error in errors:
                    print(f"         -> {error.message}")

    if not success:
        sys.exit(1)
    else:
        print("\nAll examples validated successfully.")


if __name__ == "__main__":
    main()
