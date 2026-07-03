import os

dirs = [
    "app/core",
    "app/models",
    "app/schemas",
    "app/api",
    "app/services"
]

for d in dirs:
    path = os.path.join(os.path.dirname(__file__), d)
    os.makedirs(path, exist_ok=True)
    init_path = os.path.join(path, "__init__.py")
    if not os.path.exists(init_path):
        with open(init_path, "w") as f:
            f.write(f"# Init package {d}\n")
        print(f"Created {init_path}")

print("Package directories initialized.")
