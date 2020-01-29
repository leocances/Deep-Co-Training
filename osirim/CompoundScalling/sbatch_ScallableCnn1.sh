#!/bin/sh

#SBATCH --job-name=ScallableCnn1
#SBATCH --output=%j_%t_ScallableCnn1.out
#SBATCH --error=%j_%t_ScallableCnn1.err
#SBATCH --ntasks=2
#SBATCH --cpus-per-task=5
#SBATCH --partition=GPUNodes
##SBATCH --nodelist=gpu-nc06
#SBATCH --gres=gpu:1
#SBATCH --gres-flags=enforce-binding
 
container=/logiciels/containerCollections/CUDA10/pytorch.sif
python=/users/samova/lcances/.miniconda3/envs/dl/bin/python
script=../../standalone/CompoundScalling/CompoundScalling1.py

# set up initial model architecture
init_conv="--init_conv_inputs 1 44 89 89 --init_conv_outputs 44 89 89 89"
init_linear="--init_linear_inputs 3560 --init_linear_outputs 10"
init_resolution="--init_resolution 64 173"
init_model_param="${init_conv} ${init_linear} ${init_resolution}"

fixed_parameters="--tensorboard_dir tensorboard/ScallableCnn1 ${init_model_param}"

srun -n1 -N1 singularity exec ${container} ${python} ${script} ${fixed_parameters} -t 1 2 3 4 5 6 7 8 9 -v 10 --job_name run1 &
srun -n1 -N1 singularity exec ${container} ${python} ${script} ${fixed_parameters} -t 1 2 3 4 5 6 7 8 10 -v 9 --job_name run2 &
wait
srun -n1 -N1 singularity exec ${container} ${python} ${script} ${fixed_parameters} -t 1 2 3 4 5 6 7 9 10 -v 8 --job_name run3 &
srun -n1 -N1 singularity exec ${container} ${python} ${script} ${fixed_parameters} -t 1 2 3 4 5 6 8 9 10 -v 7 --job_name run4 &
wait
srun -n1 -N1 singularity exec ${container} ${python} ${script} ${fixed_parameters} -t 1 2 3 4 5 7 8 9 10 -v 6 --job_name run5 &
srun -n1 -N1 singularity exec ${container} ${python} ${script} ${fixed_parameters} -t 1 2 3 4 6 7 8 9 10 -v 5 --job_name run6 &
wait
srun -n1 -N1 singularity exec ${container} ${python} ${script} ${fixed_parameters} -t 1 2 3 5 6 7 8 9 10 -v 4 --job_name run7 &
srun -n1 -N1 singularity exec ${container} ${python} ${script} ${fixed_parameters} -t 1 2 4 5 6 7 8 9 10 -v 3 --job_name run8 &
wait
srun -n1 -N1 singularity exec ${container} ${python} ${script} ${fixed_parameters} -t 1 3 4 5 6 7 8 9 10 -v 2 --job_name run9 &
srun -n1 -N1 singularity exec ${container} ${python} ${script} ${fixed_parameters} -t 2 3 4 5 6 7 8 9 10 -v 1 --job_name run10 &
wait
