import sys
import os
from urllib.parse import urlparse

def determine_shards_from_fai(fai_file, num_parts, margin):
    with open(fai_file, 'r') as file:
        chromosomes = file.readlines()
    total_length = sum(int(line.strip().split('\t')[1]) for line in chromosomes)
    part_size = total_length // num_parts
    extra = total_length % num_parts
    current_part_size = 0
    current_part_number = 1
    shards_list = [[] for i in range(num_parts)]
    shards_padding_list = [[] for i in range(num_parts)]
    for line in chromosomes:
        parts = line.strip().split('\t')
        chromosome_name = parts[0]
        chromosome_length = int(parts[1])
        start = 1 
        while start <= chromosome_length:
            if current_part_number == num_parts:
                end = chromosome_length + 1
            else:
                end = start + min(part_size - current_part_size + 
                                  (1 if extra > 0 else 0), chromosome_length - start + 1)
                extra -= 1 if start + part_size - current_part_size > chromosome_length and extra > 0 else 0
            current_part_size += end - start
            shards_list[current_part_number-1].append(f'{chromosome_name}:{start}-{end-1}')
            start_padded = max(1, start-margin)
            end_padded = min(end-1+margin, chromosome_length)
            shards_padding_list[current_part_number-1].append(f'{chromosome_name}:{start_padded}-{end_padded}')
            start = end
            if current_part_size >= part_size and current_part_number < num_parts:
                current_part_number += 1
                current_part_size = 0
    name_idx = [str(i).zfill(len(str(len(shards_list)))) for i in range(len(shards_list))]
    for i in range(len(shards_list)):
        with open(f"shard_interval_{name_idx[i]}.txt", 'w') as fout:
            fout.write(",".join(shards_list[i]))
    output = []
    for shards in shards_padding_list:
         output.append(",".join(shards))
    return output


def split_by_predetermined_list(shard_list):
    with open(shard_list, 'r') as file:
        chromosomes = file.readlines()
    output = []
    i = 0
    for line in chromosomes:
        chromosome_name = line.strip()
        output.append(chromosome_name)
    name_idx = [str(i).zfill(len(str(len(output)))) for i in range(len(output))]
    for i in range(len(output)):
        with open(f"shard_interval_{name_idx[i]}.txt", 'w') as fout:
            fout.write(output[i])
    return output


def urlproc(in_fname):
    files = {}
    output = []
    with open(in_fname) as fin:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            fname = os.path.split(urlparse(line).path)[-1]
            if fname.endswith('.tbi') or fname.endswith('.idx'):
                key = fname[:-4]
                if key not in files:
                    files[key] = {'idx': line}
                else:
                    files[key]['idx'] = line
            else:
                if fname not in files:
                    files[fname] = {'vcf': line}
                else:
                    files[fname]['vcf'] = line
        for k, v in files.items():
            if 'idx' not in v:
                print(f"Index file for {fname} does not exist.")
                sys.exit(1)
            if 'vcf' not in v:
                print(f"VCF file for {fname} does not exist.")
                sys.exit(1)
            output.append(f'\"{v["vcf"]}\"##idx##\"{v["idx"]}\"')
    return output


def bcftoolscmd(gvcf_list, shards_padding_list):
    name_idx = [str(i).zfill(len(str(len(shards_padding_list)))) for i in range(len(shards_padding_list))]
    for i in range(len(shards_padding_list)):
        with open(f"bcftools_cmd_{name_idx[i]}.sh", 'w') as fout:
            sample_idx = 0
            for gvcf_url in gvcf_list:
                fout.write(f"set -eo pipefail; (bcftools view --no-version -r {shards_padding_list[i]} {gvcf_url} --threads 3 -O z -o input_folder/sample-{sample_idx}.g.vcf.gz || exit 255) \n")
                sample_idx +=1


if __name__ == '__main__':
    if len(sys.argv) == 3:
        shard_list = sys.argv[1]
        gvcf_url_file = sys.argv[2]
        chr_list = split_by_predetermined_list(shard_list)
        gvcf_list = urlproc(gvcf_url_file)
        bcftoolscmd(gvcf_list, chr_list)
    elif len(sys.argv) == 5:
        fai_file_path = sys.argv[1]
        number_of_parts = int(sys.argv[2])
        margin = int(sys.argv[3])
        gvcf_url_file = sys.argv[4]
        shards_padding_list = determine_shards_from_fai(fai_file_path, number_of_parts, margin)
        gvcf_list = urlproc(gvcf_url_file)
        bcftoolscmd(gvcf_list, shards_padding_list)
    else:
        print("Usage: python partition_genome.py <FAI_FILE> <NUM_PARTS> <PADDING> <GVCF_URL_FILE>")
        print("Usage: python partition_genome.py <SHARD_LIST> <GVCF_URL_FILE>")
        sys.exit(1)
