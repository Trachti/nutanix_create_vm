# Nutanix VM Create Script

A Python script for creating virtual machines in Nutanix Prism Central through the Nutanix v3 API.

The script builds a VM payload, maps data centers and VLANs to configured Nutanix cluster and subnet UUIDs, creates the VM, optionally powers it on, and prints the resulting VM details.

## Features

- Creates a VM in Nutanix Prism Central
- Supports data center based cluster mapping
- Supports VLAN based subnet mapping
- Adds Nutanix categories to the VM metadata
- Optionally attaches a project reference
- Waits for Nutanix task completion
- Optionally powers on the VM after creation
- Prints the VM name, UUID, MAC address, power state, and categories

## Requirements

- Python 3.8 or newer
- Network access to Nutanix Prism Central
- A valid Nutanix Prism Central API token
- Cluster UUIDs and subnet UUIDs configured in the script

This project uses only the Python standard library. No external Python packages are required.

## Configuration

Before running the script, update the following values in `nutanix_vm_create.py`:

```python
NTNX_PRISMCENTRAL_IP = "YOUR_IP:9440"
CENTRAL_TOKEN = "YOUR GENERATED TOKEN FROM nutanix_auth.py"
```

Then configure your cluster UUIDs:

```python
CLUSTER_UUIDS = {
    "rz1": "UUID_from_Cluster",
    "rz2": "UUID_from_Cluster",
    "rz3": "UUID_from_Cluster",
}
```

And configure your subnet UUID mappings:

```python
SUBNET_UUIDS = {
    "rz1": {
        "1": "SUBNET_UUID_FROM_CLUSTER_1",
        "80": "SUBNET_UUID_FROM_CLUSTER_1",
    }
}
```

If you want to assign the VM to a Nutanix project, set:

```python
PROJECT_UUID = "YOUR_PROJECT_UUID"
```

Otherwise, leave it as:

```python
PROJECT_UUID = None
```

## Usage

```bash
python nutanix_vm_create.py \
  --name test-vm01 \
  --description "Test VM" \
  --cpu 2 \
  --ram 4 \
  --disk 80 \
  --rz rz1 \
  --vlan 80 \
  --power off
```

To power on the VM after creation:

```bash
python nutanix_vm_create.py \
  --name test-vm01 \
  --description "Test VM" \
  --cpu 2 \
  --ram 4 \
  --disk 80 \
  --rz rz1 \
  --vlan 80 \
  --power on
```

## Arguments

| Argument | Required | Description |
|---|---:|---|
| `--name` | Yes | Name of the VM |
| `--description` | Yes | Description of the VM |
| `--cpu` | Yes | Number of vCPUs |
| `--ram` | Yes | RAM in GiB |
| `--disk` | Yes | Disk size in GiB |
| `--rz` | Yes | Data center mapping key, one of `rz1`, `rz2`, or `rz3` |
| `--vlan` | Yes | VLAN ID, one of the configured VLAN choices |
| `--power` | No | `on` or `off`; defaults to `off` |

## Example Output

```text
Task started: 00000000-0000-0000-0000-000000000000

VM created successfully
Name: test-vm01
UUID: 00000000-0000-0000-0000-000000000000
MAC address: 50:6b:8d:00:00:00
Power state: OFF
Categories: {"CATEGORIES-KEY": "CATEGORIES-VALUE"}
```

## Security Notes

Do not commit real API tokens, passwords, cluster UUIDs, subnet UUIDs, or internal infrastructure details to a public GitHub repository.

The script currently disables SSL certificate verification by using:

```python
ssl._create_unverified_context()
```

This may be useful in lab environments, but it is not recommended for production. For production use, configure proper certificate validation.

## Disclaimer

This script is provided as an example. Test it in a safe environment before using it against production Nutanix infrastructure.
