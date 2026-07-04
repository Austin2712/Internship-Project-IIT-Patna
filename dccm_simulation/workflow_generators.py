import networkx as nx
import random
import math

class Task:
    def __init__(self, task_id, name, size, memory_req):
        self.task_id = task_id
        self.name = name
        self.size = size             # Computation size in millions of instructions (MI)
        self.memory_req = memory_req # Memory requirement in GB

def generate_montage(num_tasks=50):
    """
    Generate a Montage astronomy workflow DAG.
    N = 2X + Y + 6. With Y ~ 3X, N ~ 5X + 6 => X = (N-6)/5.
    """
    X = max(3, int(round((num_tasks - 6) / 5.0)))
    # For X, we need Y overlap diff fit jobs
    # We select overlapping pairs randomly
    pairs = []
    for i in range(X):
        for j in range(i+1, X):
            pairs.append((i, j))
    
    Y = int(round(3.0 * X))
    if Y > len(pairs):
        Y = len(pairs)
    selected_pairs = random.sample(pairs, Y)

    dag = nx.DiGraph()
    task_counter = 0

    # Level 0: mProjectPP
    project_tasks = []
    for i in range(X):
        t = Task(task_counter, f"mProjectPP_{i}", size=13.59 * 3.0, memory_req=2.0)
        dag.add_node(t.task_id, task=t)
        project_tasks.append(t)
        task_counter += 1

    # Level 1: mDiffFit
    difffit_tasks = []
    for idx, (p1, p2) in enumerate(selected_pairs):
        t = Task(task_counter, f"mDiffFit_{idx}", size=10.59 * 3.0, memory_req=2.0)
        dag.add_node(t.task_id, task=t)
        difffit_tasks.append(t)
        
        # Edges from parent projects
        dag.add_edge(project_tasks[p1].task_id, t.task_id, weight=4.16 * 1024 * 1024)
        dag.add_edge(project_tasks[p2].task_id, t.task_id, weight=4.16 * 1024 * 1024)
        task_counter += 1

    # Level 2: mConcatFit
    concat_task = Task(task_counter, "mConcatFit", size=0.08 * Y * 3.0, memory_req=4.0)
    dag.add_node(concat_task.task_id, task=concat_task)
    for dt in difffit_tasks:
        dag.add_edge(dt.task_id, concat_task.task_id, weight=273.0)
    task_counter += 1

    # Level 3: mBgModel
    bgmodel_task = Task(task_counter, "mBgModel", size=0.13 * Y * 3.0, memory_req=4.0)
    dag.add_node(bgmodel_task.task_id, task=bgmodel_task)
    dag.add_edge(concat_task.task_id, bgmodel_task.task_id, weight=209.0 * Y)
    task_counter += 1

    # Level 4: mBackground
    bg_tasks = []
    for i in range(X):
        t = Task(task_counter, f"mBackground_{i}", size=10.74 * 3.0, memory_req=2.0)
        dag.add_node(t.task_id, task=t)
        bg_tasks.append(t)
        
        # Edges from bgmodel and corresponding project
        dag.add_edge(bgmodel_task.task_id, t.task_id, weight=53.0 * X)
        dag.add_edge(project_tasks[i].task_id, t.task_id, weight=4.16 * 1024 * 1024)
        task_counter += 1

    # Level 5: mImgTbl
    imgtbl_task = Task(task_counter, "mImgTbl", size=0.37 * X * 3.0, memory_req=2.0)
    dag.add_node(imgtbl_task.task_id, task=imgtbl_task)
    for bt in bg_tasks:
        dag.add_edge(bt.task_id, imgtbl_task.task_id, weight=167.0)
    task_counter += 1

    # Level 6: mAdd
    add_task = Task(task_counter, "mAdd", size=30.11 * 3.0, memory_req=4.0)
    dag.add_node(add_task.task_id, task=add_task)
    dag.add_edge(imgtbl_task.task_id, add_task.task_id, weight=352.0 * X)
    task_counter += 1

    # Level 7: mShrink
    shrink_task = Task(task_counter, "mShrink", size=12.21 * 3.0, memory_req=4.0)
    dag.add_node(shrink_task.task_id, task=shrink_task)
    dag.add_edge(add_task.task_id, shrink_task.task_id, weight=173.0 * 1024 * 1024)
    task_counter += 1

    # Level 8: mJPEG
    jpeg_task = Task(task_counter, "mJPEG", size=10.0 * 3.0, memory_req=2.0)
    dag.add_node(jpeg_task.task_id, task=jpeg_task)
    dag.add_edge(shrink_task.task_id, jpeg_task.task_id, weight=173.0 * 1024 * 1024 / 25.0)
    task_counter += 1

    return dag

def generate_ligo(num_tasks=50):
    """
    Generate a LIGO gravitational wave Inspiral workflow DAG.
    N ~ 4X + 2Y, with Y ~ X/5.
    X = round(N / 4.4)
    """
    X = max(4, int(round(num_tasks / 4.4)))
    Y = max(1, int(round(X / 5.0)))
    Z = X

    dag = nx.DiGraph()
    task_counter = 0

    # Level 0: TmpltBank
    tmplt_tasks = []
    for i in range(X):
        t = Task(task_counter, f"TmpltBank_{i}", size=18.14 * 3.0, memory_req=2.0)
        dag.add_node(t.task_id, task=t)
        tmplt_tasks.append(t)
        task_counter += 1

    # Level 1: Inspiral (upper)
    upper_inspirals = []
    for i in range(X):
        t = Task(task_counter, f"UpperInspiral_{i}", size=460.21 * 3.0, memory_req=4.0)
        dag.add_node(t.task_id, task=t)
        upper_inspirals.append(t)
        
        # Link from tmpltbank
        dag.add_edge(tmplt_tasks[i].task_id, t.task_id, weight=987.0 * 1024)
        task_counter += 1

    # Level 2: Thinca (upper)
    upper_thincas = []
    for i in range(Y):
        t = Task(task_counter, f"UpperThinca_{i}", size=5.37 * 3.0, memory_req=2.0)
        dag.add_node(t.task_id, task=t)
        upper_thincas.append(t)
        task_counter += 1

    # Distribute upper inspirals to upper thincas
    for i, ui in enumerate(upper_inspirals):
        target_thinca = i % Y
        dag.add_edge(ui.task_id, upper_thincas[target_thinca].task_id, weight=313.0 * 1024)

    # Level 3: TrigBank
    trigbanks = []
    for i in range(Z):
        t = Task(task_counter, f"TrigBank_{i}", size=5.11 * 3.0, memory_req=2.0)
        dag.add_node(t.task_id, task=t)
        trigbanks.append(t)
        
        # Link from thincas
        source_thinca = i % Y
        dag.add_edge(upper_thincas[source_thinca].task_id, t.task_id, weight=34.0 * 1024)
        task_counter += 1

    # Level 4: Inspiral (lower)
    lower_inspirals = []
    for i in range(Z):
        t = Task(task_counter, f"LowerInspiral_{i}", size=460.21 * 3.0, memory_req=4.0)
        dag.add_node(t.task_id, task=t)
        lower_inspirals.append(t)
        
        # Link from trigbank
        dag.add_edge(trigbanks[i].task_id, t.task_id, weight=13.0 * 1024)
        task_counter += 1

    # Level 5: Thinca (lower)
    lower_thincas = []
    for i in range(Y):
        t = Task(task_counter, f"LowerThinca_{i}", size=5.37 * 3.0, memory_req=2.0)
        dag.add_node(t.task_id, task=t)
        lower_thincas.append(t)
        task_counter += 1

    # Distribute lower inspirals to lower thincas
    for i, li in enumerate(lower_inspirals):
        target_thinca = i % Y
        dag.add_edge(li.task_id, lower_thincas[target_thinca].task_id, weight=313.0 * 1024)

    return dag

def generate_cybershake(num_tasks=50):
    """
    Generate a Cybershake seismology workflow DAG.
    N = 2X*S + X + 2. With S = 4, N = 9X + 2 => X = (N-2)/9.
    """
    X = max(2, int(round((num_tasks - 2) / 9.0)))
    S = 4

    dag = nx.DiGraph()
    task_counter = 0

    zipseis_task = Task(task_counter, "ZipSeis", size=10.0 * 3.0, memory_req=2.0)
    dag.add_node(zipseis_task.task_id, task=zipseis_task)
    task_counter += 1

    zippsa_task = Task(task_counter, "ZipPSA", size=5.0 * 3.0, memory_req=2.0)
    dag.add_node(zippsa_task.task_id, task=zippsa_task)
    task_counter += 1

    for i in range(X):
        # ExtractSGT
        extract_task = Task(task_counter, f"ExtractSGT_{i}", size=137.45 * 3.0, memory_req=4.0)
        dag.add_node(extract_task.task_id, task=extract_task)
        task_counter += 1

        for j in range(S):
            # SeismogramSynthesis
            synthesis_task = Task(task_counter, f"SeismogramSynthesis_{i}_{j}", size=43.40 * 3.0, memory_req=2.0)
            dag.add_node(synthesis_task.task_id, task=synthesis_task)
            dag.add_edge(extract_task.task_id, synthesis_task.task_id, weight=230.0 * 1024 * 1024)
            task_counter += 1

            # PeakValCalcOkaya
            peakval_task = Task(task_counter, f"PeakValCalcOkaya_{i}_{j}", size=1.09 * 3.0, memory_req=1.0)
            dag.add_node(peakval_task.task_id, task=peakval_task)
            dag.add_edge(synthesis_task.task_id, peakval_task.task_id, weight=24.0 * 1024)
            task_counter += 1

            # Connect to final merge nodes
            dag.add_edge(synthesis_task.task_id, zipseis_task.task_id, weight=24.0 * 1024)
            dag.add_edge(peakval_task.task_id, zippsa_task.task_id, weight=216.0)

    return dag

def generate_epigenomics(num_tasks=50):
    """
    Generate an Epigenomics bioinformatics workflow DAG.
    N = 2L + 4L*S + 3. With S = 3, N = 14L + 3 => L = (N-3)/14.
    """
    L = max(1, int(round((num_tasks - 3) / 14.0)))
    S = 3

    dag = nx.DiGraph()
    task_counter = 0

    # Level 0: FastQSplit
    fastq_splits = []
    for i in range(L):
        t = Task(task_counter, f"FastQSplit_{i}", size=45.8 * 3.0, memory_req=2.0)
        dag.add_node(t.task_id, task=t)
        fastq_splits.append(t)
        task_counter += 1

    # Final nodes (sequential pipeline at the end)
    mapmerge2_task = Task(task_counter, "FinalMapMerge", size=30.0 * 3.0, memory_req=4.0)
    dag.add_node(mapmerge2_task.task_id, task=mapmerge2_task)
    task_counter += 1

    maqindex_task = Task(task_counter, "MaqIndex", size=5.0 * 3.0, memory_req=2.0)
    dag.add_node(maqindex_task.task_id, task=maqindex_task)
    dag.add_edge(mapmerge2_task.task_id, maqindex_task.task_id, weight=500.0 * 1024 * 1024)
    task_counter += 1

    pileup_task = Task(task_counter, "PileUp", size=100.0 * 3.0, memory_req=4.0)
    dag.add_node(pileup_task.task_id, task=pileup_task)
    dag.add_edge(maqindex_task.task_id, pileup_task.task_id, weight=100.0 * 1024 * 1024)
    task_counter += 1

    mapmerge1_tasks = []
    for i in range(L):
        # mapMerge1 for each lane
        mm1 = Task(task_counter, f"MapMerge1_{i}", size=30.0 * 3.0, memory_req=4.0)
        dag.add_node(mm1.task_id, task=mm1)
        mapmerge1_tasks.append(mm1)
        dag.add_edge(mm1.task_id, mapmerge2_task.task_id, weight=100.0 * 1024 * 1024)
        task_counter += 1

        for j in range(S):
            # FilterContams
            fc = Task(task_counter, f"FilterContams_{i}_{j}", size=8.26 * 3.0, memory_req=2.0)
            dag.add_node(fc.task_id, task=fc)
            dag.add_edge(fastq_splits[i].task_id, fc.task_id, weight=70.0 * 1024 * 1024)
            task_counter += 1

            # Sol2Sanger
            s2s = Task(task_counter, f"Sol2Sanger_{i}_{j}", size=4.6 * 3.0, memory_req=2.0)
            dag.add_node(s2s.task_id, task=s2s)
            dag.add_edge(fc.task_id, s2s.task_id, weight=70.0 * 1024 * 1024)
            task_counter += 1

            # Fast2Bfq
            f2b = Task(task_counter, f"Fast2Bfq_{i}_{j}", size=10.3 * 3.0, memory_req=2.0)
            dag.add_node(f2b.task_id, task=f2b)
            dag.add_edge(s2s.task_id, f2b.task_id, weight=50.0 * 1024 * 1024)
            task_counter += 1

            # MaqMap
            mm = Task(task_counter, f"MaqMap_{i}_{j}", size=100.0 * 3.0, memory_req=4.0)
            dag.add_node(mm.task_id, task=mm)
            dag.add_edge(f2b.task_id, mm.task_id, weight=12.0 * 1024 * 1024)
            
            # Connect MaqMap to lane mapMerge1
            dag.add_edge(mm.task_id, mm1.task_id, weight=10.0 * 1024 * 1024)
            task_counter += 1

    return dag

def get_workflow_generator(name):
    generators = {
        "Montage": generate_montage,
        "Ligo": generate_ligo,
        "Cybershake": generate_cybershake,
        "Epigenomics": generate_epigenomics
    }
    return generators.get(name)
