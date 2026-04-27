import zipfile
import xml.etree.ElementTree as ET

def explore_sensors(file_path):
    print(f"\nExploring Sensors in: {file_path}")
    with zipfile.ZipFile(file_path, 'r') as z:
        content = z.open('main.xml').read().decode('utf-8')
        root = ET.fromstring(content)
        # Look for Sensor tags
        for sensor in root.findall('.//Sensor'):
            name = sensor.get('Name')
            id_val = sensor.get('ID')
            euid = sensor.get('EUID')
            print(f"Sensor Name: {name}, ID: {id_val}, EUID: {euid}")
            # Also check attributes of parent Interface if possible
            # But ET doesn't have parent easily. We'll search for common serial number patterns.

if __name__ == "__main__":
    explore_sensors('inputs\\002.cap')
    explore_sensors('inputs\\022.cap')
