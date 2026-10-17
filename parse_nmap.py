#!/usr/bin/env python3

import sys
import xml.etree.ElementTree as ET

def get_scan_scope(filename):
    tree = ET.parse(filename)
    root = tree.getroot()

    scope = []

    for scan in root.findall("scaninfo"):
        protocol = scan.get("protocol")
        scan_type = scan.get("type")
        services = scan.get("services", "")

        scope.append((protocol, scan_type, services))

    return sorted(scope)


def check_host_status(filename):
    tree = ET.parse(filename)
    root = tree.getroot()

    hosts = root.findall("./host")

    if len(hosts) != 1:
        raise ValueError(
            f"Expected exactly 1 host, found {len(hosts)}"
        )

    status = hosts[0].find("status")

    if status is None:
        raise ValueError("Host status missing")

    state = status.get("state")

    if state != "up":
        raise ValueError(
            f"Host is not reachable (state: {state})"
        )

    return True


def get_extra_ports(filename):
    tree = ET.parse(filename)
    root = tree.getroot()

    extra_ports = []

    for extra in root.findall("./host/ports/extraports"):
        state = extra.get("state", "unknown")
        count = int(extra.get("count", "0"))

        extra_ports.append((state, count))

    return sorted(extra_ports)


def expand_ports(services):
    result = set()

    for item in services.split(","):
        if "-" in item:
            start, end = map(int, item.split("-"))
            result.update(range(start, end + 1))
        else:
            result.add(int(item))

    return result



def validate_scan(filename):
    tree = ET.parse(filename)
    root = tree.getroot()

    scan = root.find("scaninfo")

    if scan is None:
        raise ValueError("Missing scaninfo element")

    expected = int(scan.get("numservices"))

    ports = root.findall("./host/ports/port")
    extra = root.findall("./host/ports/extraports")

    # 1. Check for duplicate port entries
    port_keys = []

    for port in ports:
        protocol = port.get("protocol")
        number = port.get("portid")

        if not protocol or not number:
            raise ValueError("Missing port protocol or number")

        port_keys.append((protocol, int(number)))

    if len(port_keys) != len(set(port_keys)):
        raise ValueError(
            f"Duplicate port entries found in {filename}"
        )

    # 2. Verify that reported ports were scanned
    scanned_ports = expand_ports(scan.get("services", ""))

    if len(scanned_ports) != expected:
        raise ValueError(
            "Scan scope count does not match port list"
        )

    for protocol, number in port_keys:
        if protocol != scan.get("protocol"):
            raise ValueError(
                f"Unexpected protocol: {protocol}"
            )

        if number not in scanned_ports:
            raise ValueError(
                f"Port {number}/{protocol} was not scanned"
            )

    # 3. Check total port count
    actual = len(ports) + sum(
        int(item.get("count")) for item in extra
    )

    if expected != actual:
        raise ValueError(
            f"Inconsistent port count in {filename}: "
            f"expected {expected}, found {actual}"
        )



def get_host_identity(filename):
    tree = ET.parse(filename)
    root = tree.getroot()

    hosts = root.findall("./host")

    if len(hosts) != 1:
        raise ValueError("Expected exactly one host")

    ip = None
    mac = None

    for address in hosts[0].findall("address"):
        if address.get("addrtype") == "ipv4":
            ip = address.get("addr")

        elif address.get("addrtype") == "mac":
            mac = address.get("addr")

    if not ip:
        raise ValueError("Missing IPv4 address")

    return ip, mac


def parse_scan(filename):
    tree = ET.parse(filename)
    root = tree.getroot()
    ports = {}

    for port in root.findall("./host/ports/port"):
        protocol = port.get("protocol")
        number = port.get("portid")

        state_element = port.find("state")
        service_element = port.find("service")

        state = (
            state_element.get("state", "unknown")
            if state_element is not None else "unknown"
        )

        service = (
            service_element.get("name", "unknown")
            if service_element is not None else "unknown"
        )

        product = (
            service_element.get("product", "")
            if service_element is not None else ""
        )

        version = (
            service_element.get("version", "")
            if service_element is not None else ""
        )

        ports[(protocol, int(number))] = (
            state, service, product, version
        )

    return ports


def compare_scans(old_file, new_file):

    old_scope = get_scan_scope(old_file)
    new_scope = get_scan_scope(new_file)

    if not old_scope or not new_scope:
        raise ValueError("Missing scan scope information")

    if old_scope != new_scope:
        raise ValueError(
            "Scan scope mismatch: different ports or scan types"
        )
    check_host_status(old_file)
    check_host_status(new_file)
    validate_scan(old_file)
    validate_scan(new_file)


    # Verify that both scans belong to the same device
    old_ip, old_mac = get_host_identity(old_file)
    new_ip, new_mac = get_host_identity(new_file)

    if old_ip != new_ip:
        raise ValueError(
            f"Host IP mismatch: {old_ip} != {new_ip}"
        )

    if old_mac and new_mac and old_mac.lower() != new_mac.lower():
        raise ValueError(
            f"Host MAC mismatch: {old_mac} != {new_mac}"
        )


    old_extra = get_extra_ports(old_file)
    new_extra = get_extra_ports(new_file)

    extra_changed = old_extra != new_extra

    old_ports = parse_scan(old_file)
    new_ports = parse_scan(new_file)

    all_ports = sorted(
        set(old_ports) | set(new_ports)
    )

    changes = 0

    for key in all_ports:
        old = old_ports.get(key)
        new = new_ports.get(key)

        if old != new:
            protocol, number = key
            print(f"CHANGE: {number}/{protocol}")
            print(f"  OLD: {old}")
            print(f"  NEW: {new}")
            changes += 1

    # This block must be OUTSIDE the for loop

    if extra_changed:
        print("CHANGE: Grouped port statistics")
        print(f"  OLD: {old_extra}")
        print(f"  NEW: {new_extra}")

    if changes == 0 and not extra_changed:
        print("No port or service changes detected.")
        return 0

    print(f"\nTotal changed ports: {changes}")
    print(f"Grouped port statistics changed: {extra_changed}")
    return 1


if __name__ == "__main__":
    if len(sys.argv) == 2:
        ports = parse_scan(sys.argv[1])

        for (protocol, number), details in sorted(ports.items()):
            print(f"{number}/{protocol} | {' | '.join(details)}")

    elif len(sys.argv) == 3:
        try:
            sys.exit(compare_scans(sys.argv[1], sys.argv[2]))
        except (OSError, ET.ParseError, ValueError) as error:
            print(f"ERROR: {error}", file=sys.stderr)
            sys.exit(2)

    else:
        print("Usage:")
        print("  python3 parse_nmap.py scan.xml")
        print("  python3 parse_nmap.py old.xml new.xml")
        sys.exit(1)
