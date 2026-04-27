with open('refer_results/002.csv', 'r') as f:
    lines = f.readlines()
    print(f"Total lines: {len(lines)}")
    for line in lines[-10:]:
        print(line.strip())
