#!/bin/sh

#SBATCH --job-name=10_dct_scallable2
#SBATCH --output=%j_%t_10_dct_scallable2.out
#SBATCH --error=%j_%t_10_dct_scallable2.err
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=5
#SBATCH --partition=GPUNodes
##SBATCH --nodelist=gpu-nc06
#SBATCH --gres=gpu:1
#SBATCH --gres-flags=enforce-binding
 
container=/logiciels/containerCollections/CUDA10/pytorch.sif
python=/users/samova/lcances/.miniconda3/envs/dl/bin/python
script=../standalone/co-training_scallable2.py
fixed_parameters="--epochs 600 -T tensorboard/0.5r_scallable2_cross_validation --ratio 0.1"
hyper_parameters="--base_lr 0.01 --epsilon 0.02 --lambda_cot_max 2 --lambda_diff_max 0.5 --warm_up 120"
    
srun -n1 -N1 singularity exec ${container} ${python} ${script} ${fixed_parameters} ${hyper_parameters} -t 1 2 3 4 5 6 7 8 9 -v 10 --job_name run1 &
srun -n1 -N1 singularity exec ${container} ${python} ${script} ${fixed_parameters} ${hyper_parameters} -t 1 2 3 4 5 6 7 8 10 -v 9 --job_name run2 &
srun -n1 -N1 singularity exec ${container} ${python} ${script} ${fixed_parameters} ${hyper_parameters} -t 1 2 3 4 5 6 7 9 10 -v 8 --job_name run3 &
srun -n1 -N1 singularity exec ${container} ${python} ${script} ${fixed_parameters} ${hyper_parameters} -t 1 2 3 4 5 6 8 9 10 -v 7 --job_name run4 &
wait
srun -n1 -N1 singularity exec ${container} ${python} ${script} ${fixed_parameters} ${hyper_parameters} -t 1 2 3 4 5 7 8 9 10 -v 6 --job_name run5 &
srun -n1 -N1 singularity exec ${container} ${python} ${script} ${fixed_parameters} ${hyper_parameters} -t 1 2 3 4 6 7 8 9 10 -v 5 --job_name run6 &
srun -n1 -N1 singularity exec ${container} ${python} ${script} ${fixed_parameters} ${hyper_parameters} -t 1 2 3 5 6 7 8 9 10 -v 4 --job_name run7 &
srun -n1 -N1 singularity exec ${container} ${python} ${script} ${fixed_parameters} ${hyper_parameters} -t 1 2 4 5 6 7 8 9 10 -v 3 --job_name run8 &
wait
srun -n1 -N1 singularity exec ${container} ${python} ${script} ${fixed_parameters} ${hyper_parameters} -t 1 3 4 5 6 7 8 9 10 -v 2 --job_name run9 &
srun -n1 -N1 singularity exec ${container} ${python} ${script} ${fixed_parameters} ${hyper_parameters} -t 2 3 4 5 6 7 8 9 10 -v 1 --job_name run10 &
wait
