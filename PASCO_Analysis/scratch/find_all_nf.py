import zipfile
import re

def find_all_nf(file_path):
    with zipfile.ZipFile(file_path, 'r') as z:
        if 'main.xml' in z.namelist():
            with z.open('main.xml') as f:
                content = f.read().decode('utf-8')
                
                # Find all Normal Force DataSources
                matches = re.finditer(r'<DataSource[^>]+MeasurementName="Normal Force".*?</DataSource>', content, re.DOTALL)
                for i, m in enumerate(matches):
                    block = m.group(0)
                    name = re.search(r'MeasurementName="([^"]+)"', block).group(1)
                    channel = re.search(r'ChannelIDName="([^"]+)"', block).group(1) if re.search(r'ChannelIDName="([^"]+)"', block) else "Unknown"
                    print(f"NF {i+1}: Name={name}, Channel={channel}")
                    
                    datasets = block.split('<DataSet')[1:]
                    for j, ds in enumerate(datasets):
                        ds_block = ds.split('</DataSet>')[0]
                        file_match = re.search(r'FileName="([^"]+)"', ds_block)
                        group_match = re.search(r'DataGroupNumber="([^"]+)"', ds_block)
                        if file_match:
                            print(f"  Run {j+1} (Group {group_match.group(1) if group_match else '?'}): {file_match.group(1)}")

if __name__ == "__main__":
    find_all_nf('inputs\\002.cap')
