import copy
import os
import sys

import yaml
from django.core.management import (
    BaseCommand,
    call_command,
)
from yaml import (
    CSafeDumper,
    CSafeLoader,
)


RELATED_FIELD_PARAM_NAME = "related_field"

JSON_API_CONTENT_TYPE = "application/vnd.api+json"


def kebab_to_camel(s: str) -> str:
    if s == "AuthorizedAccount":
        return "AuthorizedStorageAccount"
    elif s == "ConfiguredAddon":
        return "ConfiguredStorageAddon"
    s = s.title()
    parts = s.split("-")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


def fix_resource(s: str) -> str:
    if s == "AuthorizedAccount":
        return "authorized-storage-account"
    elif s == "ConfiguredAddon":
        return "configured-storage-addon"
    return s


def get_schema_from_ref(openapi_data, ref):
    """
    Resolves a $ref string to its corresponding schema object in the OpenAPI data.
    Example: '#/components/schemas/Article' -> openapi_data['components']['schemas']['Article']
    """
    parts = ref.strip("#/").split("/")
    node = openapi_data
    for part in parts:
        if part in node:
            node = node[part]
        else:
            return None
    return node


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default="openapi.yml",
        )

    def handle(self, *args, **options):
        call_command("spectacular", file=".openapi.yml")
        with open(".openapi.yml") as buf:
            data = yaml.load(buf, CSafeLoader)
        os.remove(".openapi.yml")

        if "paths" not in data:
            print("Warning: No 'paths' object found in the YAML file. Nothing to do.")
            yaml.dump(data, sys.stdout)
            return

        paths = data["paths"]
        new_paths = {}
        paths_to_delete = []

        print("🔍 Starting scan for generic relationship endpoints...")
        reverse_path_index = {
            path_item["get"]["operationId"].replace("_", "-"): path_item
            for path, path_item in paths.items()
            if "get" in path_item
        }

        for path, path_item in paths.items():
            if path.endswith(f"/{{{RELATED_FIELD_PARAM_NAME}}}/"):
                print(f"  -> Found generic relationship path: {path}")
                paths_to_delete.append(path)

                base_path = path.rsplit("/", 2)[0] + "/"
                primary_resource_path = f"{base_path}"

                if primary_resource_path not in paths:
                    print(
                        f"    [!] Warning: Could not find parent path '{primary_resource_path}' to infer relationships. Skipping."
                    )
                    continue

                try:
                    # We assume the 'get' operation on the primary resource defines its schema
                    schema_ref: str = paths[primary_resource_path]["get"]["responses"][
                        "200"
                    ]["content"][JSON_API_CONTENT_TYPE]["schema"]["$ref"]
                    primary_resource_schema = get_schema_from_ref(
                        data, schema_ref.removesuffix("Response")
                    )
                except KeyError:
                    print(
                        f"    [!] Warning: Could not find a valid 200 OK schema reference for '{primary_resource_path}'. Skipping."
                    )
                    continue

                if not primary_resource_schema:
                    print(
                        f"    [!] Warning: Could not resolve schema reference '{schema_ref}'. Skipping."
                    )
                    continue

                try:
                    relationships = primary_resource_schema["properties"][
                        "relationships"
                    ]["properties"]
                except KeyError:
                    print(
                        f"    [!] Warning: No 'properties.relationships.properties' found in schema for '{primary_resource_path}'. Skipping."
                    )
                    continue

                print(f"    Found relationships: {', '.join(relationships.keys())}")

                for rel_name, rel_schema in relationships.items():
                    new_path_str = f"{base_path}{rel_name}"
                    resource: str = rel_schema["properties"]["data"].get(
                        "properties",
                        rel_schema["properties"]["data"]
                        .get("items", {})
                        .get("properties"),
                    )["type"]["enum"][0]
                    # if resource.endswith('s'):
                    resource = resource.removesuffix("s")
                    # schema_name = f'Paginated{kebab_to_camel(resource)}List'
                    # else:
                    schema_name = f"{kebab_to_camel(resource)}Response"
                    new_schema_ref = f"#/components/schemas/{schema_name}"
                    new_path_item = copy.deepcopy(
                        reverse_path_index.get(f"{fix_resource(resource)}s-retrieve")
                    )
                    if not new_path_item:
                        new_path_item = copy.deepcopy(path_item)

                    method = "get"
                    operation = new_path_item[method]
                    operation["operationId"] = (
                        f"{path_item[method]['operationId']}_related_{rel_name}"
                    )
                    operation["tags"] = path_item[method]["tags"]
                    if "parameters" in operation:
                        operation["parameters"] = [
                            p
                            for p in operation["parameters"]
                            if p.get("name") != RELATED_FIELD_PARAM_NAME
                        ]

                    try:
                        operation["responses"]["200"]["content"][JSON_API_CONTENT_TYPE][
                            "schema"
                        ] = {"$ref": new_schema_ref}
                        print(
                            f"      ✓ Creating endpoint '{method.upper()} {new_path_str}'"
                        )
                        print(f"        - Pointing schema to: {new_schema_ref}")

                    except KeyError:
                        print(
                            f"    [!] Warning: Could not find a valid response structure in '{method.upper()} {path}' to rewire the schema."
                        )

                    new_paths[new_path_str] = {"get": operation}

        output_file = options["output"]
        if paths_to_delete:
            print("\n🔄 Updating OpenAPI structure...")
            for path in paths_to_delete:
                del data["paths"][path]
                print(f"  - Removed generic path: {path}")

            data["paths"].update(new_paths)
            for path in new_paths:
                print(f"  + Added specific path: {path}")

            # Dump the modified data to the output file
            with open(output_file, "w") as f:
                yaml.dump(data, f)
            print(f"\n✅ Success! Wrote refined OpenAPI spec to '{output_file}'")
        else:
            print(
                "\n✅ No generic relationship paths found to modify. Output file is unchanged."
            )
            # Optionally write to output file anyway
            with open(output_file, "w") as f:
                yaml.dump(data, f, CSafeDumper)
