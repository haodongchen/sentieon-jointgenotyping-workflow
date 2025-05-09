cwlVersion: v1.2
class: CommandLineTool
doc: "Split by chromosome. Intended to run in a workflow, but can be run as standalone"
label: split_by_chr
$namespaces:
  sbg: https://sevenbridges.com

requirements:
- class: ShellCommandRequirement
- class: ResourceRequirement
  coresMin: $(inputs.threads)
- class: DockerRequirement
  dockerPull: pgc-images.sbgenomics.com/hdchen/sentieon:202308.02_cavatica_patched
- class: InlineJavascriptRequirement
- class: EnvVarRequirement
  envDef:
  - envName: SENTIEON_LICENSE
    envValue: $(inputs.sentieon_license)

baseCommand: [bash -c]
arguments:
- position: 0
  shellQuote: false
  valueFrom: >-
    'set -eo pipefail; cat $(inputs.chr_list.path) | xargs -P $(inputs.threads) -ICHR bash -c "set -eo pipefail; bcftools view -r CHR $(inputs.input_vcf.path) | sentieon util vcfconvert - CHR_$(inputs.input_vcf.nameroot).g.vcf.gz"'

inputs:
  input_vcf: { type: File, secondaryFiles: ['.tbi'] }
  chr_list: { type: File }
  chr_array: { type: 'string[]', doc: "chr list as str array"}
  threads: { type: 'int?', default: 3 }
  sentieon_license: { type: string, doc: "Sentieon license server IP and port"}
outputs:
  split_vcfs:
    type: 'File[]'
    secondaryFiles: ['.tbi']
    outputBinding:
      glob: '*.vcf.gz'
      outputEval: |
        ${
          var order = inputs.chr_array;
          return self.sort(function(a, b) { return order.indexOf(a.basename.split('_').shift()) - order.indexOf(b.basename.split('_').shift()) } );
        }
