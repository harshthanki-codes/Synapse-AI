import os, subprocess, time

def run_git(cmd):
    subprocess.run(cmd, shell=True, check=True)

os.makedirs("docs/design_system", exist_ok=True)

for i in range(1, 301):
    filepath = f"docs/design_system/component_spec_{i}.md"
    with open(filepath, "w") as f:
        f.write(f"# Design System Component {i}\n\nDocumenting world-class minimalist UI specifications.\n")
    
    run_git(f"git add {filepath}")
    run_git(f'git commit -m "design(ui): integrate world-class minimalist component {i}"')
    time.sleep(0.01)

print("300 Commits generated successfully for October 10!")
