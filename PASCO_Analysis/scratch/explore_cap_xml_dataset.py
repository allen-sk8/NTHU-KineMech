import zipfile
import re

def find_dataset_mapping(file_path, dataset_id):
    with zipfile.ZipFile(file_path, 'r') as z:
        if 'main.xml' in z.namelist():
            with z.open('main.xml') as f:
                content = f.read().decode('utf-8')
                match = re.search(f'.{{0,2000}}{re.escape(dataset_id)}.{{0,2000}}', content, re.DOTALL)
                if match:
                    print(match.group(0))

if __name__ == "__main__":
    find_dataset_mapping('inputs/002.cap', '{c42f726d-0958-4173-962f-228e20ce53c4}')
