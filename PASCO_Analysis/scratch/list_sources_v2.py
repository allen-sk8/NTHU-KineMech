import zipfile
import re

def list_all_data(file_path):
    with zipfile.ZipFile(file_path, 'r') as z:
        if 'main.xml' in z.namelist():
            with z.open('main.xml') as f:
                content = f.read().decode('utf-8')
                
                # Split content by <DataSource to avoid memory issues and parse each
                parts = content.split('<DataSource')[1:]
                for p in parts:
                    source_xml = '<DataSource' + p.split('</DataSource>')[0] + '</DataSource>'
                    name_match = re.search(r'MeasurementName="([^"]+)"', source_xml)
                    channel_match = re.search(r'ChannelIDName="([^"]+)"', source_xml)
                    name = name_match.group(1) if name_match else "Unknown"
                    channel = channel_match.group(1) if channel_match else "Unknown"
                    
                    if "Force" in name or "xxx-" in channel:
                        print(f"Source: {name}, Channel: {channel}")
                        # Find DataSets
                        datasets = re.findall(r'<DataSet[^>]+>', source_xml)
                        for i, ds in enumerate(datasets):
                            file_match = re.search(r'FileName="([^"]+)"', ds)
                            if file_match:
                                print(f"  Run {i+1}: {file_match.group(1)}")

if __name__ == "__main__":
    list_all_data('inputs\\002.cap')
