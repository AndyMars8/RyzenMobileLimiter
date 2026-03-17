# Ryzen Mobile Limiter
A simplified power management utility for laptops with AMD Ryzen APU.
## Acknowledgements
This project relies on [FlyGoat/RyzenAdj](https://github.com/FlyGoat/RyzenAdj) for functionality and wouldn't be possible without its existence.
## ⚠️ Disclaimer ⚠️
Manipulation of hardware power registers may cause system instability. Use at your own risk!
Research your hardware specifications for safe limits before applying them.

For more information about supported APU architectures, visit RyzenAdj's [Supported Models page](https://github.com/FlyGoat/RyzenAdj/wiki/Supported-Models).

***\*A device I own has an AMD Ryzen 7 7840HS (Phoenix). Although it's not listed on the Supported Models page, I can personally confirm that setting temperature and power limits work as intended.***
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

    ./python3 --version
Clone this repository and then follow the [RyzenAdj build guide](https://github.com/FlyGoat/RyzenAdj?tab=readme-ov-file#linux) for Linux in order to copy the compiled library.

    git clone https://github.com/AndyMars8/RyzenMobileLimiter.git
    cd RyzenMobileLimiter && mkdir lib
    cp /path/to/RyzenAdj/build/libryzenadj.so lib
Test run the daemon:

    sudo ryzenm-limit start
If the daemon doesn't start, you need to have the [ryzen_smu](https://github.com/amkillam/ryzen_smu) kernel module installed (which is mentioned in the guide above) or have the kernel parameter ```iomem=relaxed``` loaded at boot. A successful initialisation should show the message below without errors:

    [INFO] yyyy-mm-dd hh:mm:ss - Started RyzenMobileLimiter daemon
On a separate terminal, run a command to check if the daemon has successfully processed it (Example: ```./ryzenm-limit -t 90 -p 35```):

    [INFO] yyyy-mm-dd hh:mm:ss - Successfully set tctl_temp to 90°C
    [INFO] yyyy-mm-dd hh:mm:ss - Successfully set stapm_limit to 35W
    [INFO] yyyy-mm-dd hh:mm:ss - Successfully set fast_limit to 35W
    [INFO] yyyy-mm-dd hh:mm:ss - Successfully set slow_limit to 35W

If you wish for these values to persist, keep the daemon running.
