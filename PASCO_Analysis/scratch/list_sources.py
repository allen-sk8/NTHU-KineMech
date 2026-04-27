import zipfile
import xml.etree.ElementTree as ET

def list_all_data(file_path):
    try:
        with zipfile.ZipFile(file_path, 'r') as z:
            if 'main.xml' in z.namelist():
                with z.open('main.xml') as f:
                    content = f.read().decode('utf-8')
                    # Use a regex to find DataSources if ET fails
                    import re
                    sources = re.findall(r'<DataSource[^>]+>', content)
                    print(f"Found {len(sources)} DataSources")
                    for s in sources:
                        name = re.search(r'MeasurementName="([^"]+)"', s)
                        short = re.search(r'ShortName="([^"]+)"', s)
                        channel = re.search(r'ChannelIDName="([^"]+)"', s)
                        print(f"Source: {name.group(1) if name else 'N/A'} ({short.group(1) if short else 'N/A'}), Channel: {channel.group(1) if channel else 'N/A'}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_all_data('inputs\\002.cap')
