# olfactory-ble-controller

### How To Flash
1. Install Python.
2. Install the [ESP-IDF Tools](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/get-started/windows-setup.html).
    1. Make sure you get the latest ESP-IDF offline installer on the installers page.
    2. Download the installer and install (this will take a little).
3. Open a powershell window in the `esp-olfactory-ble-controller` directory.
4. Run the following commands while replacing `X.X.X` with the version of ESP-IDF you installed.
    1. `C:\Espressif\frameworks\esp-idf-vX.X.X\install.ps1`
    2. `C:\Espressif\frameworks\esp-idf-vX.X.X\export.ps1`
5. Enter the following command to build the project: `idf.py build`.
6. Enter the following command to flash the project: `idf.py flash`.
7. Enter the following command to monitor the device: `idf.py monitor`.

### How to Connect
1. Install Python.
2. Open a powershell window in the `py-olfactory-ble-controller` directory.
3. Enter the command `python -m venv venv` to make a virtual environment in the directory.
4. Enter the command `.\venv\Scripts\activate.bat` to enter the virtual environment.
5. Enter the command `pip install -r requirements.txt` to install the required packages.
6. Enter the command `python main.py` to run the program.