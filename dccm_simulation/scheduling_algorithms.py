import networkx as nx
from vm_model import VMInstance, VM_TYPES, calculate_monetary_cost
import math

def compute_upward_ranks(dag):
    """
    Compute upward ranks (UR) for all tasks in the DAG.
    UR_i = avg_ETC_i + max_{j in succ(i)} (avg_DT_ij + UR_j)
    """
    nodes = list(nx.topological_sort(dag))
    ranks = {}
    for node in reversed(nodes):
        task = dag.nodes[node]['task']
        avg_etc = sum(task.size / vt.ecu for vt in VM_TYPES) / len(VM_TYPES)
        max_succ_val = 0.0
        for succ in dag.successors(node):
            edge_data = dag.get_edge_data(node, succ)
            data_size = edge_data.get('weight', 0.0)
            avg_dt = sum(data_size / vt.bandwidth for vt in VM_TYPES) / len(VM_TYPES)
            val = avg_dt + ranks[succ]
            if val > max_succ_val:
                max_succ_val = val
        ranks[node] = avg_etc + max_succ_val
    return ranks

def compute_downward_ranks(dag):
    """
    Compute downward ranks (DR) for all tasks in the DAG.
    DR_i = max_{j in pred(i)} (DR_j + avg_ETC_j + avg_DT_ji)
    """
    nodes = list(nx.topological_sort(dag))
    ranks = {}
    for node in nodes:
        max_pred_val = 0.0
        for pred in dag.predecessors(node):
            pred_task = dag.nodes[pred]['task']
            edge_data = dag.get_edge_data(pred, node)
            data_size = edge_data.get('weight', 0.0)
            avg_dt = sum(data_size / vt.bandwidth for vt in VM_TYPES) / len(VM_TYPES)
            avg_etc_pred = sum(pred_task.size / vt.ecu for vt in VM_TYPES) / len(VM_TYPES)
            val = ranks[pred] + avg_etc_pred + avg_dt
            if val > max_pred_val:
                max_pred_val = val
        ranks[node] = max_pred_val
    return ranks

def find_earliest_gap(dag, task, instance, scheduled_tasks, delta):
    """
    Find the earliest start and end time for a task on a VM instance,
    supporting insertion in idle slots.
    """
    task_id = task.task_id
    
    # Calculate ready time based on predecessor finish times and communication costs
    ready_time = 0.0
    for pred in dag.predecessors(task_id):
        pred_inst, pred_start, pred_end = scheduled_tasks[pred]
        if pred_inst.instance_id == instance.instance_id:
            dt = 0.0
        else:
            edge_data = dag.get_edge_data(pred, task_id)
            data_size = edge_data.get('weight', 0.0)
            dt = data_size / pred_inst.vm_type.bandwidth
        ready_time = max(ready_time, pred_end + dt)

    etc = task.size / instance.vm_type.ecu

    # If the instance is new (no tasks scheduled yet), it requires boot delay delta
    if not instance.tasks:
        start_time = ready_time + delta
        return start_time, start_time + etc

    # Sort tasks by start time to find gaps
    sorted_tasks = sorted(instance.tasks, key=lambda x: x[1])
    
    # Check gap before the first task
    first_start = sorted_tasks[0][1]
    # VM boot time is delta seconds before the first scheduled task starts
    vm_boot_time = max(0.0, sorted_tasks[0][1] - delta)
    if first_start - max(ready_time, vm_boot_time) >= etc:
        start_time = max(ready_time, vm_boot_time)
        return start_time, start_time + etc

    # Check gaps between tasks
    for i in range(len(sorted_tasks) - 1):
        gap_start = sorted_tasks[i][2]
        gap_end = sorted_tasks[i+1][1]
        if gap_end - max(ready_time, gap_start) >= etc:
            start_time = max(ready_time, gap_start)
            return start_time, start_time + etc

    # Place at the end
    last_end = sorted_tasks[-1][2]
    start_time = max(ready_time, last_end)
    return start_time, start_time + etc

def schedule_heft(dag, vm_types, max_instances=16, delta=100.0):
    """
    HEFT algorithm: sorts by upward rank and schedules on the VM minimizing EFT.
    """
    upward_ranks = compute_upward_ranks(dag)
    sorted_nodes = sorted(dag.nodes(), key=lambda n: upward_ranks[n], reverse=True)
    
    instances = []
    scheduled_tasks = {}  # task_id -> (instance, start, end)
    
    for node in sorted_nodes:
        task = dag.nodes[node]['task']
        best_instance = None
        best_start = float('inf')
        best_end = float('inf')
        
        # Enforce memory constraint and handle fallbacks
        allowed_vts = [vt for vt in vm_types if vt.memory >= task.memory_req]
        if not allowed_vts:
            allowed_vts = [next(vt for vt in VM_TYPES if vt.memory >= task.memory_req)]
            
        # 1. Try existing instances
        for inst in instances:
            if inst.vm_type.memory < task.memory_req:
                continue
            start, end = find_earliest_gap(dag, task, inst, scheduled_tasks, delta)
            if end < best_end:
                best_end = end
                best_start = start
                best_instance = inst
                
        # 2. Try booting a new instance of allowed VM types
        if len(instances) < max_instances:
            for vt in allowed_vts:
                temp_inst = VMInstance(vt, f"heft_vm_{len(instances)}")
                start, end = find_earliest_gap(dag, task, temp_inst, scheduled_tasks, delta)
                if end < best_end:
                    best_end = end
                    best_start = start
                    best_instance = (vt, len(instances))
                    
        if best_instance is None:
            # Force boot a fallback
            vt = allowed_vts[0]
            best_instance = (vt, len(instances))
            
        # Apply scheduling decision
        if isinstance(best_instance, tuple):
            vt, idx = best_instance
            new_inst = VMInstance(vt, f"heft_vm_{idx}")
            instances.append(new_inst)
            best_instance = new_inst
            start, end = find_earliest_gap(dag, task, best_instance, scheduled_tasks, delta)
            best_start, best_end = start, end
            
        best_instance.tasks.append((node, best_start, best_end))
        best_instance.avail_time = max(best_instance.avail_time, best_end)
        scheduled_tasks[node] = (best_instance, best_start, best_end)
        
    return instances, scheduled_tasks

def schedule_bdheft(dag, vm_types, global_deadline, max_instances=16, delta=100.0):
    """
    BDHEFT algorithm: distributes deadlines, schedules on cheap VMs meeting deadlines.
    """
    upward_ranks = compute_upward_ranks(dag)
    downward_ranks = compute_downward_ranks(dag)
    sorted_nodes = sorted(dag.nodes(), key=lambda n: upward_ranks[n], reverse=True)
    
    # Compute sub-deadlines based on downward rank
    longest_path = 0.0
    for node in dag.nodes():
        task = dag.nodes[node]['task']
        avg_etc = sum(task.size / vt.ecu for vt in vm_types) / len(vm_types)
        longest_path = max(longest_path, downward_ranks[node] + avg_etc)
        
    sub_deadlines = {}
    for node in dag.nodes():
        task = dag.nodes[node]['task']
        avg_etc = sum(task.size / vt.ecu for vt in vm_types) / len(vm_types)
        if longest_path > 0:
            sub_deadlines[node] = global_deadline * ((downward_ranks[node] + avg_etc) / longest_path)
        else:
            sub_deadlines[node] = global_deadline

    instances = []
    scheduled_tasks = {}
    
    for node in sorted_nodes:
        task = dag.nodes[node]['task']
        sub_dl = sub_deadlines[node]
        
        allowed_vts = [vt for vt in vm_types if vt.memory >= task.memory_req]
        if not allowed_vts:
            allowed_vts = [next(vt for vt in VM_TYPES if vt.memory >= task.memory_req)]
            
        valid_options = []
        
        # Try existing instances
        for inst in instances:
            if inst.vm_type.memory < task.memory_req:
                continue
            start, end = find_earliest_gap(dag, task, inst, scheduled_tasks, delta)
            curr_cost = inst.cost
            inst.tasks.append((node, start, end))
            inc_cost = inst.cost - curr_cost
            inst.tasks.pop()
            valid_options.append((inst, start, end, inc_cost))
            
        # Try booting new instances
        if len(instances) < max_instances:
            for vt in allowed_vts:
                temp_inst = VMInstance(vt, f"bdheft_vm_{len(instances)}")
                start, end = find_earliest_gap(dag, task, temp_inst, scheduled_tasks, delta)
                inc_cost = temp_inst.cost
                valid_options.append(((vt, len(instances)), start, end, inc_cost))
                
        if not valid_options:
            vt = allowed_vts[0]
            temp_inst = VMInstance(vt, f"bdheft_vm_{len(instances)}")
            start, end = find_earliest_gap(dag, task, temp_inst, scheduled_tasks, delta)
            valid_options.append(((vt, len(instances)), start, end, temp_inst.cost))
            
        # Filter options meeting sub-deadline
        feasible = [opt for opt in valid_options if opt[2] <= sub_dl]
        
        if feasible:
            best_opt = min(feasible, key=lambda x: (x[3], x[2]))
        else:
            best_opt = min(valid_options, key=lambda x: x[2])
            
        best_instance_info, start, end, _ = best_opt
        
        if isinstance(best_instance_info, tuple):
            vt, idx = best_instance_info
            new_inst = VMInstance(vt, f"bdheft_vm_{idx}")
            instances.append(new_inst)
            best_instance = new_inst
            start, end = find_earliest_gap(dag, task, best_instance, scheduled_tasks, delta)
        else:
            best_instance = best_instance_info
            
        best_instance.tasks.append((node, start, end))
        best_instance.avail_time = max(best_instance.avail_time, end)
        scheduled_tasks[node] = (best_instance, start, end)
        
    return instances, scheduled_tasks

def schedule_bdas(dag, vm_types, global_deadline, max_instances=16, delta=100.0):
    """
    BDAS algorithm: worthiness-based scheduling balancing time and cost.
    """
    upward_ranks = compute_upward_ranks(dag)
    downward_ranks = compute_downward_ranks(dag)
    sorted_nodes = sorted(dag.nodes(), key=lambda n: upward_ranks[n], reverse=True)
    
    longest_path = 0.0
    for node in dag.nodes():
        task = dag.nodes[node]['task']
        avg_etc = sum(task.size / vt.ecu for vt in vm_types) / len(vm_types)
        longest_path = max(longest_path, downward_ranks[node] + avg_etc)
        
    sub_deadlines = {}
    for node in dag.nodes():
        task = dag.nodes[node]['task']
        avg_etc = sum(task.size / vt.ecu for vt in vm_types) / len(vm_types)
        if longest_path > 0:
            sub_deadlines[node] = global_deadline * ((downward_ranks[node] + avg_etc) / longest_path)
        else:
            sub_deadlines[node] = global_deadline

    instances = []
    scheduled_tasks = {}
    
    for node in sorted_nodes:
        task = dag.nodes[node]['task']
        sub_dl = sub_deadlines[node]
        
        allowed_vts = [vt for vt in vm_types if vt.memory >= task.memory_req]
        if not allowed_vts:
            allowed_vts = [next(vt for vt in VM_TYPES if vt.memory >= task.memory_req)]
            
        candidates = []
        
        # Existing instances
        for inst in instances:
            if inst.vm_type.memory < task.memory_req:
                continue
            start, end = find_earliest_gap(dag, task, inst, scheduled_tasks, delta)
            curr_cost = inst.cost
            inst.tasks.append((node, start, end))
            inc_cost = inst.cost - curr_cost
            inst.tasks.pop()
            candidates.append((inst, start, end, inc_cost))
            
        # New instances
        if len(instances) < max_instances:
            for vt in allowed_vts:
                if vt.memory < task.memory_req:
                    continue
                temp_inst = VMInstance(vt, f"bdas_vm_{len(instances)}")
                start, end = find_earliest_gap(dag, task, temp_inst, scheduled_tasks, delta)
                inc_cost = temp_inst.cost
                candidates.append(((vt, len(instances)), start, end, inc_cost))
                
        if not candidates:
            vt = allowed_vts[0]
            temp_inst = VMInstance(vt, f"bdas_vm_{len(instances)}")
            start, end = find_earliest_gap(dag, task, temp_inst, scheduled_tasks, delta)
            candidates.append(((vt, len(instances)), start, end, temp_inst.cost))
            
        feasible = [c for c in candidates if c[2] <= sub_dl]
        
        if feasible:
            min_ft = min(c[2] for c in feasible)
            max_ft = max(c[2] for c in feasible)
            min_c = min(c[3] for c in feasible)
            max_c = max(c[3] for c in feasible)
            
            best_opt = None
            max_worthiness = -1.0
            
            for c in feasible:
                inst_info, start, end, cost = c
                norm_time = (max_ft - end) / (max_ft - min_ft + 1e-6)
                norm_cost = (max_c - cost) / (max_c - min_c + 1e-6)
                worthiness = norm_time * 0.3 + norm_cost * 0.7
                if worthiness > max_worthiness:
                    max_worthiness = worthiness
                    best_opt = c
            
            if best_opt is None:
                best_opt = feasible[0]
        else:
            best_opt = min(candidates, key=lambda x: x[2])
            
        best_instance_info, start, end, _ = best_opt
        
        if isinstance(best_instance_info, tuple):
            vt, idx = best_instance_info
            new_inst = VMInstance(vt, f"bdas_vm_{idx}")
            instances.append(new_inst)
            best_instance = new_inst
            start, end = find_earliest_gap(dag, task, best_instance, scheduled_tasks, delta)
        else:
            best_instance = best_instance_info
            
        best_instance.tasks.append((node, start, end))
        best_instance.avail_time = max(best_instance.avail_time, end)
        scheduled_tasks[node] = (best_instance, start, end)
        
    return instances, scheduled_tasks

def get_task_levels(dag):
    """
    Get levels of tasks in DAG.
    """
    levels = {}
    nodes = list(nx.topological_sort(dag))
    for node in nodes:
        max_pred_lvl = -1
        for pred in dag.predecessors(node):
            max_pred_lvl = max(max_pred_lvl, levels[pred])
        levels[node] = max_pred_lvl + 1
    return levels

def schedule_dccm(dag, vm_types, global_deadline, max_instances=16, delta=100.0):
    """
    Proposed DCCM (Deadline-Constrained Cost Minimisation) algorithm.
    """
    levels = get_task_levels(dag)
    max_level = max(levels.values())
    
    # Filter VM types feasible for the entire workflow memory-wise
    max_mem_req = max(dag.nodes[node]['task'].memory_req for node in dag.nodes())
    feasible_vms = [vt for vt in vm_types if vt.memory >= max_mem_req]
    if not feasible_vms:
        feasible_vms = [vm_types[-1]]
        
    # Select VMcheap
    vm_cheap = feasible_vms[0]
    for vt in feasible_vms:
        instances, sched_tasks = schedule_heft(dag, [vt], max_instances, delta)
        makespan = max(t[2] for t in sched_tasks.values()) if sched_tasks else 0.0
        if makespan <= global_deadline:
            vm_cheap = vt
            break
    else:
        vm_cheap = feasible_vms[-1]
        
    # Baseline schedule on vm_cheap
    base_instances, base_sched = schedule_heft(dag, [vm_cheap], max_instances, delta)
    base_makespan = max(t[2] for t in base_sched.values()) if base_sched else 0.0
    
    at_w = max(0.0, global_deadline - base_makespan)
    
    level_etc = {}
    total_etc = 0.0
    for node in dag.nodes():
        task = dag.nodes[node]['task']
        lvl = levels[node]
        etc = task.size / vm_cheap.ecu
        level_etc[lvl] = level_etc.get(lvl, 0.0) + etc
        total_etc += etc
        
    level_slack = {}
    cumulative_slack = {}
    running_slack = 0.0
    for lvl in range(max_level + 1):
        etc_gl = level_etc.get(lvl, 0.0)
        at_gl = (etc_gl / total_etc) * at_w if total_etc > 0 else 0.0
        level_slack[lvl] = at_gl
        running_slack += at_gl
        cumulative_slack[lvl] = running_slack
        
    sub_deadlines = {}
    for node in dag.nodes():
        lvl = levels[node]
        base_finish = base_sched[node][2]
        sub_deadlines[node] = base_finish + cumulative_slack[lvl]

    upward_ranks = compute_upward_ranks(dag)
    sorted_nodes = sorted(dag.nodes(), key=lambda n: (levels[n], -upward_ranks[n]))
    
    instances = []
    scheduled_tasks = {}
    
    for node in sorted_nodes:
        task = dag.nodes[node]['task']
        sub_dl = sub_deadlines[node]
        
        allowed_vts = [vt for vt in vm_types if vt.memory >= task.memory_req]
        if not allowed_vts:
            allowed_vts = [next(vt for vt in VM_TYPES if vt.memory >= task.memory_req)]
            
        valid_options = []
        
        # Try existing instances
        for inst in instances:
            if inst.vm_type.memory < task.memory_req:
                continue
            start, end = find_earliest_gap(dag, task, inst, scheduled_tasks, delta)
            curr_cost = inst.cost
            inst.tasks.append((node, start, end))
            inc_cost = inst.cost - curr_cost
            inst.tasks.pop()
            valid_options.append((inst, start, end, inc_cost))
            
        # Try booting new instances
        if len(instances) < max_instances:
            for vt in allowed_vts:
                temp_inst = VMInstance(vt, f"dccm_vm_{len(instances)}")
                start, end = find_earliest_gap(dag, task, temp_inst, scheduled_tasks, delta)
                inc_cost = temp_inst.cost
                valid_options.append(((vt, len(instances)), start, end, inc_cost))
                
        if not valid_options:
            vt = allowed_vts[0]
            temp_inst = VMInstance(vt, f"dccm_vm_{len(instances)}")
            start, end = find_earliest_gap(dag, task, temp_inst, scheduled_tasks, delta)
            valid_options.append(((vt, len(instances)), start, end, temp_inst.cost))
            
        feasible = [opt for opt in valid_options if opt[2] <= sub_dl]
        
        if feasible:
            best_opt = min(feasible, key=lambda x: (x[3], x[2]))
        else:
            best_opt = min(valid_options, key=lambda x: x[2])
            
        best_instance_info, start, end, _ = best_opt
        
        if isinstance(best_instance_info, tuple):
            vt, idx = best_instance_info
            new_inst = VMInstance(vt, f"dccm_vm_{idx}")
            instances.append(new_inst)
            best_instance = new_inst
            start, end = find_earliest_gap(dag, task, best_instance, scheduled_tasks, delta)
        else:
            best_instance = best_instance_info
            
        best_instance.tasks.append((node, start, end))
        best_instance.avail_time = max(best_instance.avail_time, end)
        scheduled_tasks[node] = (best_instance, start, end)
        
    return instances, scheduled_tasks
