import zipfile
import xml.etree.ElementTree as ET

def list_sources(file_path):
    with zipfile.ZipFile(file_path, 'r') as z:
        if 'main.xml' in z.namelist():
            with z.open('main.xml') as f:
                content = f.read().decode('utf-8')
                root = ET.fromstring(content)
                for ds in root.findall('.//DataSource'):
                    m_name = ds.get('MeasurementName')
                    c_id = ds.get('ChannelIDName')
                    euid = ds.get('EUID')
                    if m_name == "Normal Force":
                        print(f"Normal Force: ChannelIDName={c_id}, EUID={euid}")

if __name__ == "__main__":
    list_sources('inputs\\002.cap')
