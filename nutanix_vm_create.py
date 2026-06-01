import http.client
import json
import argparse
import time
import ssl

NTNX_PRISMCENTRAL_IP = "YOUR_IP:9440"
CENTRAL_TOKEN = "YOUR GENERATED TOKEN FROM nutanix_auth.py"

CLUSTER_UUIDS = {
    "rz1": "UUID_from_Cluster",
    "rz2": "UUID_from_Cluster",
    "rz3": "UUID_from_Cluster",
}

SUBNET_UUIDS = {
    "rz1": {
        "1": "SUBNET_UUID_FROM_CLUSTER_1",
        "2": "SUBNET_UUID_FROM_CLUSTER_1",
        "3": "SUBNET_UUID_FROM_CLUSTER_1",
        "80": "SUBNET_UUID_FROM_CLUSTER_1",
        "130": "SUBNET_UUID_FROM_CLUSTER_1",
        "190": "SUBNET_UUID_FROM_CLUSTER_1",
        "191": "SUBNET_UUID_FROM_CLUSTER_1",
    },
    "rz2": {
        "1": "SUBNET_UUID_FROM_CLUSTER_2",
        "2": "SUBNET_UUID_FROM_CLUSTER_2",
        "3": "SUBNET_UUID_FROM_CLUSTER_2",
        "80": "SUBNET_UUID_FROM_CLUSTER_2",
        "130": "SUBNET_UUID_FROM_CLUSTER_2",
        "190": "SUBNET_UUID_FROM_CLUSTER_2",
        "191": "SUBNET_UUID_FROM_CLUSTER_2",
    },
    "rz3": {
        "1": "SUBNET_UUID_FROM_CLUSTER_3",
        "2": "SUBNET_UUID_FROM_CLUSTER_3",
        "3": "SUBNET_UUID_FROM_CLUSTER_3",
        "80": "SUBNET_UUID_FROM_CLUSTER_3",
        "130": "SUBNET_UUID_FROM_CLUSTER_3",
        "190": "SUBNET_UUID_FROM_CLUSTER_3",
    }
}

PROJECT_UUID = None


def get_conn():
    context = ssl._create_unverified_context()
    return http.client.HTTPSConnection(NTNX_PRISMCENTRAL_IP, context=context)


def api_request(method, url, payload=None):
    conn = get_conn()
    headers = {
        "Accept": "application/json",
        "Authorization": CENTRAL_TOKEN,
        "Content-Type": "application/json"
    }

    body = None
    if payload is not None:
        body = payload if isinstance(payload, str) else json.dumps(payload)

    conn.request(method, url, body=body, headers=headers)
    res = conn.getresponse()
    raw = res.read().decode("utf-8")

    try:
        data = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        data = {"raw": raw}

    if res.status >= 400:
        raise RuntimeError(f"API error {res.status} on {url}: {data}")

    return data


def get_vm_by_name(server):
    offset = 0
    while offset <= 500:
        payload = {
            "kind": "vm",
            "length": 50,
            "offset": offset
        }
        data = api_request("POST", "/api/nutanix/v3/vms/list", payload)
        entities = data.get("entities", [])

        for elem in entities:
            if elem.get("spec", {}).get("name") == server:
                return elem

        if not entities:
            break
        offset += 50

    return None


def get_vm(uuid_):
    return api_request("GET", f"/api/nutanix/v3/vms/{uuid_}")


def wait_for_task(task_uuid, timeout=300, interval=5):
    url = f"/api/nutanix/v3/tasks/{task_uuid}"
    start = time.time()

    while time.time() - start < timeout:
        data = api_request("GET", url)
        status = data.get("status", "").upper()

        if status in {"SUCCEEDED", "FAILED", "ABORTED"}:
            return data

        time.sleep(interval)

    raise TimeoutError(f"Task {task_uuid} reached timeout after {timeout}s.")


def build_categories(rz):
    categories = {}

    rz = rz.lower()
    if rz == "rz1":
        categories["CATEGORIES-KEY"] = "CATEGORIES-VALUE"
    elif rz == "rz2":
        categories["CATEGORIES-KEY"] = "CATEGORIES-VALUE"

    return categories


def build_vm_payload(name, description, cpu, ram_gib, disk_gib, rz, vlan):
    rz = rz.lower()
    vlan = str(vlan)

    if rz not in CLUSTER_UUIDS:
        raise ValueError(f"Invalid data center: {rz}")

    if rz not in SUBNET_UUIDS or vlan not in SUBNET_UUIDS[rz]:
        raise ValueError(f"No subnet mapping found for data center={rz}, VLAN={vlan}")

    cluster_uuid = CLUSTER_UUIDS[rz]
    subnet_uuid = SUBNET_UUIDS[rz][vlan]

    metadata = {
        "kind": "vm",
        "categories": build_categories(rz),
        "use_categories_mapping": False
    }

    if PROJECT_UUID:
        metadata["project_reference"] = {
            "kind": "project",
            "uuid": PROJECT_UUID
        }

    payload = {
        "metadata": metadata,
        "spec": {
            "name": name,
            "description": description,
            "cluster_reference": {
                "kind": "cluster",
                "uuid": cluster_uuid
            },
            "resources": {
                "num_sockets": 1,
                "num_vcpus_per_socket": cpu,
                "num_threads_per_core": 1,
                "memory_size_mib": ram_gib * 1024,
                "power_state": "OFF",
                "disk_list": [
                    {
                        "device_properties": {
                            "disk_address": {
                                "adapter_type": "SCSI",
                                "device_index": 0
                            },
                            "device_type": "DISK"
                        },
                        "disk_size_mib": disk_gib * 1024
                    },
                    {
                        "device_properties": {
                            "disk_address": {
                                "adapter_type": "SATA",
                                "device_index": 1
                            },
                            "device_type": "CDROM"
                        }
                    }
                ],
                "nic_list": [
                    {
                        "nic_type": "NORMAL_NIC",
                        "model": "VIRTIO",
                        "is_connected": True,
                        "subnet_reference": {
                            "kind": "subnet",
                            "uuid": subnet_uuid
                        }
                    }
                ]
            }
        }
    }

    return payload


def update_vm_power_state(vm_uuid, target_state):
    vm_data = get_vm(vm_uuid)

    if "status" in vm_data:
        del vm_data["status"]

    vm_data["spec"]["resources"]["power_state"] = target_state.upper()

    response = api_request("PUT", f"/api/nutanix/v3/vms/{vm_uuid}", vm_data)

    task_uuid = (
        response.get("status", {}).get("execution_context", {}).get("task_uuid")
        or response.get("task_uuid")
        or response.get("status", {}).get("task_uuid")
    )

    if task_uuid:
        print(f"Power-{target_state.upper()} task started: {task_uuid}")
        task_result = wait_for_task(task_uuid)
        task_status = task_result.get("status", "").upper()

        if task_status != "SUCCEEDED":
            error_detail = task_result.get("error_detail", "Unknown error")
            raise RuntimeError(f"Power-{target_state.upper()} failed: {error_detail}")


def create_vm(name, description, cpu, ram_gib, disk_gib, rz, vlan, power="off"):
    existing = get_vm_by_name(name)
    if existing:
        raise RuntimeError(f"A VM with the name '{name}' already exists.")

    payload = build_vm_payload(
        name=name,
        description=description,
        cpu=cpu,
        ram_gib=ram_gib,
        disk_gib=disk_gib,
        rz=rz,
        vlan=vlan
    )

    response = api_request("POST", "/api/nutanix/v3/vms", payload)

    task_uuid = (
        response.get("status", {}).get("execution_context", {}).get("task_uuid")
        or response.get("task_uuid")
        or response.get("status", {}).get("task_uuid")
    )

    if task_uuid:
        print(f"Task started: {task_uuid}")
        task_result = wait_for_task(task_uuid)
        task_status = task_result.get("status", "").upper()

        if task_status != "SUCCEEDED":
            error_detail = task_result.get("error_detail", "Unknown error")
            error_code = task_result.get("error_code", "n/a")
            entity_refs = task_result.get("entity_reference_list", [])
            print(f"Task error code: {error_code}")
            print(f"Task error detail: {error_detail}")
            print(f"Entity references: {entity_refs}")
            raise RuntimeError(f"VM creation failed: {error_detail}")

    vm = get_vm_by_name(name)
    if not vm:
        raise RuntimeError("VM was created but could not be found afterwards.")

    vm_uuid = vm["metadata"]["uuid"]

    if power.lower() == "on":
        print(f"Powering on VM {name} ...")
        update_vm_power_state(vm_uuid, "ON")
    else:
        update_vm_power_state(vm_uuid, "OFF")

    full_vm = get_vm(vm_uuid)

    nics = full_vm.get("spec", {}).get("resources", {}).get("nic_list", [])
    if not nics:
        nics = full_vm.get("status", {}).get("resources", {}).get("nic_list", [])

    mac = nics[0].get("mac_address") if nics else None
    power_state = (
        full_vm.get("status", {}).get("resources", {}).get("power_state")
        or full_vm.get("spec", {}).get("resources", {}).get("power_state")
    )

    return {
        "name": full_vm.get("spec", {}).get("name"),
        "uuid": vm_uuid,
        "mac_address": mac,
        "categories": full_vm.get("metadata", {}).get("categories", {}),
        "power_state": power_state
    }


def main():
    parser = argparse.ArgumentParser(description="Create a Nutanix VM")
    parser.add_argument("--name", required=True, type=str, help="VM name")
    parser.add_argument("--description", required=True, type=str, help="Description")
    parser.add_argument("--cpu", required=True, type=int, help="Number of vCPUs")
    parser.add_argument("--ram", required=True, type=int, help="RAM in GiB")
    parser.add_argument("--disk", required=True, type=int, help="Disk size in GiB")
    parser.add_argument("--rz", required=True, choices=["rz1", "rz2", "rz3"], help="Data center")
    parser.add_argument(
        "--vlan",
        required=True,
        choices=["1", "2", "3", "80", "130", "190", "191"],
        help="VLAN"
    )
    parser.add_argument(
        "--power",
        required=False,
        choices=["on", "off"],
        default="off",
        help="Power on the VM after creation or leave it powered off"
    )

    args = parser.parse_args()

    result = create_vm(
        name=args.name,
        description=args.description,
        cpu=args.cpu,
        ram_gib=args.ram,
        disk_gib=args.disk,
        rz=args.rz,
        vlan=args.vlan,
        power=args.power
    )

    print("\nVM created successfully")
    print(f"Name: {result['name']}")
    print(f"UUID: {result['uuid']}")
    print(f"MAC address: {result['mac_address']}")
    print(f"Power state: {result['power_state']}")
    print(f"Categories: {json.dumps(result['categories'], ensure_ascii=False)}")


if __name__ == "__main__":
    main()
