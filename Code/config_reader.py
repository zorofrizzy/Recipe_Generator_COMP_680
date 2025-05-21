import configparser
import os

# Path to the config file : Desktop/Comp_583/ElasticSearch/config.ini

BASE_PATH = os.path.expanduser("~/Desktop")
CONFIG_FILE_PATH = os.path.join(BASE_PATH, "COMP 680", "Recipe_Generator", "config.ini") 


#Function to read a config INI file.
def fetch_config_dict(file_path = CONFIG_FILE_PATH, section=None):
    """
    Convert INI file to a dictionary.
    
    Args:
        file_path (str): Path to the INI file.
        section (str, optional): Name of the section to retrieve. If None, returns all sections.
    
    Returns:
        dict: Dictionary containing the configuration data.
    """
    config = configparser.ConfigParser()
    config.read(file_path)
    
    config_dict = {}
    for section_name in config.sections():
        if section is None or section_name == section:
            for option, value in config.items(section_name):
                config_dict[option] = value
    
    return config_dict


#print(fetch_config_dict())