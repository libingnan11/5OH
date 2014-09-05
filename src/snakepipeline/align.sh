#!/usr/bin/env bash

#BSUB -J align
#BSUB -e align.%J.%I.err
#BSUB -o align.%J.%I.out
#BSUB -q normal
#BSUB -n 6

<<DOC
Align the reads!
Input: DATA + {sample}.umi.fq.gz
Params: BOWTIEIDX, ALIGN_ARGS
Output: DATA + {sample}.UMIs_not_removed.align.align.{align_mode}.bam
DOC

set -o nounset -o pipefail -o errexit -x

# Read variables from command line
if [[ $# == 3 ]]; then
    fastq=$1
    BOWTIEIDX=$2
    umibam=$3
    align_arg=""
fi

if [[ $# == 4 ]]; then
    fastq=$1
    BOWTIEIDX=$2
    align_arg=$3
    umibam=$4
fi

zcat $fastq \
    | bowtie $align_arg --sam $BOWTIEIDX -p 6 - \
    | samtools view -ShuF4 - \
    | samtools sort -o - $umibam.temp -m 8G \
        > $umibam
samtools index $umibam