import math

class VMInstance:
    def __init__(self, vm_type, instance_id):
        self.vm_type = vm_type
        self.instance_id = instance_id
        self.tasks = []  # List of scheduled tasks: (task_id, start_time, end_time)
        self.avail_time = 0.0

    @property
    def start_time(self):
        if not self.tasks:
            return 0.0
        return min(t[1] for t in self.tasks)

    @property
    def end_time(self):
        if not self.tasks:
            return 0.0
        return max(t[2] for t in self.tasks)

    @property
    def lease_duration(self):
        if not self.tasks:
            return 0.0
        return self.end_time - self.start_time

    @property
    def cost(self):
        duration_hours = math.ceil(self.lease_duration / 3600.0)
        return duration_hours * self.vm_type.price

class VMType:
    def __init__(self, name, memory, ecu, price):
        self.name = name
        self.memory = memory  # in GB
        self.ecu = ecu        # CPU capacity in ECU
        self.price = price    # price per hour in $
        # Assume bandwidth is proportional to ECU (e.g. 100 Mbps per 1 ECU)
        # 1 ECU = 100 Mbps = 12.5 MB/s
        self.bandwidth = ecu * 12.5 * 1024 * 1024  # in bytes/second

# Table 2: VM Instance Specifications
VM_TYPES = [
    VMType("m3.medium", 3.75, 3.0, 0.067),
    VMType("m4.large", 8.0, 6.5, 0.126),
    VMType("m3.xlarge", 15.0, 13.0, 0.266),
    VMType("m4.2xlarge", 32.0, 26.0, 0.504),
    VMType("m4.4xlarge", 64.0, 53.5, 1.008),
    VMType("m4.10xlarge", 160.0, 124.5, 2.520)
]

def calculate_monetary_cost(instances):
    """
    Calculate the total monetary cost of a list of leased VM instances.
    """
    return sum(inst.cost for inst in instances)
