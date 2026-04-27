import zipfile
import xml.etree.ElementTree as ET

def list_all_data(file_path):
    with zipfile.ZipFile(file_path, 'r') as z:
        if 'main.xml' in z.namelist():
            with z.open('main.xml') as f:
                content = f.read().decode('utf-8')
                root = ET.fromstring(content)
                for source in root.findall('.//DataSource'):
                    name = source.get('MeasurementName')
                    short_name = source.get('ShortName')
                    long_name = source.get('LongName')
                    channel = source.get('ChannelIDName')
                    print(f"Source: {name} ({short_name}), Channel: {channel}")
                    for i, dataset in enumerate(source.findall('.//DataSet')):
                        run_id = dataset.get('DataSetID')
                        group = dataset.get('DataGroupNumber')
                        storage = dataset.find('.//DependentStorageElement')
                        if storage is not None:
                            filename = storage.get('FileName')
                            print(f"  Run {i+1} (Group {group}): {filename}")

if __name__ == "__main__":
    list_all_data('inputs/002.cap')
