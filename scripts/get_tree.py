import os
import sys

def get_tree(target_path):
    for root, dirs, files in os.walk(target_path):
        dirs[:] = [d for d in dirs if d not in ('.venv', '.git', '__pycache__', 'node_modules', 'reports')]
        for file in sorted(files):
            if file.endswith(('.py', '.yml', '.yaml', '.sql', '.ini', '.env', '.md', '.txt')):
                print(os.path.join(root, file))

if __name__ == '__main__':
    get_tree(sys.argv[1])
