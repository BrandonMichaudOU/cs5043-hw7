#!/bin/bash
#
#SBATCH --partition=debug
#SBATCH --cpus-per-task=16
#SBATCH --mem=16G
#SBATCH --output=outputs/hw7_%j_stdout.txt
#SBATCH --error=outputs/hw7_%j_stderr.txt
#SBATCH --time=00:30:00
#SBATCH --job-name=hw7
#SBATCH --mail-user=brandondmichaud@ou.edu
#SBATCH --mail-type=ALL
#SBATCH --chdir=/home/cs504319/cs5043-hw7

. /home/fagg/tf_setup.sh
conda activate dnn_2024_02


python hw7_base.py -vv @exp.txt @oscer.txt @discriminator.txt @generator.txt @meta.txt --cpus_per_task $SLURM_CPUS_PER_TASK
