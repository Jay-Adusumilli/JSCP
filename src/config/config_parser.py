def read_config_folder(folder_path: str) -> dict:
    """
    Reads all configuration files in the specified folder and returns a dictionary
    with the file names (without extension) as keys and their content as values.

    :param folder_path: Path to the folder containing configuration files.
    :return: Dictionary with file names as keys and file content as values.
    """
    import os
    import yaml

    config_data = {}

    for filename in os.listdir(folder_path):
        if filename.endswith('.yaml'):
            file_path = os.path.join(folder_path, filename)
            with open(file_path, 'r') as file:
                config_data[os.path.splitext(filename)[0]] = yaml.safe_load(file)

    return config_data