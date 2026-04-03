# Ryzen Mobile Limiter
A simplified power management utility for laptops with AMD Ryzen APU.
## Acknowledgements
This project relies on [FlyGoat/RyzenAdj](https://github.com/FlyGoat/RyzenAdj) for functionality and wouldn't be possible without its existence.
## ⚠️ Disclaimer ⚠️
> [!WARNING]
> Manipulation of hardware power registers may cause system instability. Use at your own risk!
> Research your hardware specifications for safe limits before applying them.

For more information about supported APU architectures, visit RyzenAdj's [Supported Models page](https://github.com/FlyGoat/RyzenAdj/wiki/Supported-Models).

> [!NOTE]
> A device I own has an AMD Ryzen 7 7840HS (Phoenix). Although it's not listed on the Supported Models page, I can personally confirm that setting temperature and power limits work as intended for that particular model.
## Usage
Ryzen Mobile Limiter's purpose is to enforce APU temperature and power limits. Demo commands are listed below.
### Temperature Limit
Setting temperature limit of 90°C:

    ./ryzenm-limit --temp-limit 90
or in a more concise format:

    ./ryzenm-limit -t 90
### Power Limit
Setting overall power limit to 40W:

    ./ryzenm-limit --power-limit 40
or

    ./ryzenm-limit -p 40

For more fine-tuned power limits to account for performance in short bursts:

    ./ryzenm-limit --stapm-limit=35 --fast-limit=54 --slow-limit=45
or

    ./ryzenm-limit -q 35 54 45
More information on these particular options are documented [here](https://github.com/FlyGoat/RyzenAdj/wiki/Renoir-Tuning-Guide#--stapm-limit--stapm-limit).
## Setup Instructions
### Linux
Ensure the system has Git and Python 3.9 or newer installed, which can be verified with:

    python3 --version
Clone this repository and then follow the [RyzenAdj build guide](https://github.com/FlyGoat/RyzenAdj?tab=readme-ov-file#linux) for Linux in order to copy the compiled library.

    git clone https://github.com/AndyMars8/RyzenMobileLimiter.git
    cd RyzenMobileLimiter && mkdir lib
    cp /path/to/RyzenAdj/build/libryzenadj.so lib/
Test run the daemon:

    sudo ./ryzenm-limit start
> [!NOTE]
> If the daemon doesn't start, you need to have the [ryzen_smu](https://github.com/amkillam/ryzen_smu) kernel module installed and loaded (which is mentioned in the guide above) or have the kernel parameter ```iomem=relaxed``` loaded at boot. A successful initialisation should show the message below without errors:
> ```bash
> [INFO] yyyy-mm-dd hh:mm:ss - Started RyzenMobileLimiter daemon
> ```
> On a separate terminal, run a command to check if the daemon has successfully processed it (Example: ```./ryzenm-limit -t 90 -p 35```):
 
    [INFO] yyyy-mm-dd hh:mm:ss - Successfully set tctl_temp to 90°C
    [INFO] yyyy-mm-dd hh:mm:ss - Successfully set stapm_limit to 35W
    [INFO] yyyy-mm-dd hh:mm:ss - Successfully set fast_limit to 35W
    [INFO] yyyy-mm-dd hh:mm:ss - Successfully set slow_limit to 35W

If you wish for these values to persist, keep the daemon running.
## Installation
### Linux
After following the setup instructions above, Ryzen Mobile Limiter can be installed by copying the following files/directories to their respective directories in the root file system:

    sudo cp ryzenm-limit /usr/local/bin/
    sudo cp -r src/ /usr/local/src/ryzenm-limit/
    sudo cp -r lib/ /usr/local/lib/ryzenm-limit/
    sudo cp -r config/ /etc/ryzenm-limit/
> [!NOTE]
> If entering ```sudo ryzenm-limit``` returns ```sudo: ryzenm-limit: command not found```, you'll need to add ```/usr/local/bin``` to ```secure_path```:

    sudo visudo
> Or edit with a text editor of your choice (Example: nano):

    sudo EDITOR=nano visudo
> Find these lines:

    ## Use this PATH instead of the user's to find commands.
    Defaults secure_path="/usr/sbin:/usr/bin:/sbin:/bin"
> Then add the required path to ```secure_path```:

    Defaults secure_path="/usr/sbin:/usr/bin:/sbin:/bin:/usr/local/bin"
#### Systemd
If you wish to run Ryzen Mobile Limiter in the background at system startup, you can use the provided Systemd service:

    sudo cp systemd/ryzenm-limit.service /etc/systemd/system/
    sudo systemctl enable --now ryzenm-limit.service
