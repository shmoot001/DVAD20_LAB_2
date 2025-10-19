# 🚀 How to Run the Code

### 1. Stop any running controllers
```bash
sudo killall ovs-testcontroller
sudo pkill -f ryu-manager
````

### 2. Activate Ryu environment

```bash
conda activate ryu
```

### 3. Start the Ryu controller

```bash
ryu-manager rr_lb.py --verbose
```

Keep this terminal open to see controller logs.

### 4. Run the experiment (in a new terminal)

```bash
sudo python3 experiment.py
```

This starts Mininet, generates traffic, and logs flow completion times (`flows.jsonl`, `stats.csv`).

### 5. Clean up (optional)

```bash
sudo mn -c
```

**Summary**

| Step                 | Command                                                        |
| -------------------- | -------------------------------------------------------------- |
| Stop old controllers | `sudo killall ovs-testcontroller && sudo pkill -f ryu-manager` |
| Activate env         | `conda activate ryu`                                           |
| Start Ryu            | `ryu-manager rr_lb.py --verbose`                               |
| Run experiment       | `sudo python3 experiment.py`                                   |
| Clean up             | `sudo mn -c`                                                   |

