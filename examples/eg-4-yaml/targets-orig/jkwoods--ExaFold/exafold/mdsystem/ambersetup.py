#!/usr/bin/env python

__all__ = ["tri", "linear_peptide"]

import yaml
import subprocess

"""Functions to assist with conversion of FASTA or txt file
with single letter amino acid sequence (i.e., "NLYIQWLKDGG..")
to AmberTools topology and coordinate files for use in OpenMM
System.

Functions
_________
tri ::
	helper function to convert single letter amino acid
	sequence to 3-letter sequence

linear_peptide ::
	from a FASTA or txt file path, generate an linear peptide
	in amber; optionally also takes a protein name to use
	in saved files and a forcefield file path. Default
	forcefield is ff14SB, specified as the best for proteins
	in the AmberTools18 manual (2018)

"""


def tri(x):
        return {
                'A': 'ALA',
                'R': 'ARG',
                'N': 'ASN',
                'D': 'ASP',
                'C': 'CYS',
                'Q': 'GLN',
                'E': 'GLU',
                'G': 'GLY',
                'H': 'HIS',
                'I': 'ILE',
                'L': 'LEU',
                'K': 'LYS',
                'M': 'MET',
                'F': 'PHE',
                'P': 'PRO',
                'S': 'SER',
                'T': 'THR',
                'W': 'TRP',
                'Y': 'TYR',
                'V': 'VAL'
        }.get(x, '')

def linear_peptide():

	with open("my_parameters.yaml", 'r') as stream:
		try:
			parameters = yaml.safe_load(stream)
		except yaml.YAMLError as exc:
			print(exc)

	fasta = parameters['fasta']
	name = parameters['name']
	forcefield = parameters['forcefield']

	f = open(fasta, "r")
	lines = f.readlines()
	seq = ""
	for l in lines:
	        if (not (l.startswith(">") or l.startswith(";"))):
        	        seq = seq + l

	f.close()
	seq = seq.replace("\n", "") #clean

	triseq = "{ "
        for i,s in enumerate(seq):
            if (i==0):
                triseq = triseq + "N"
            elif (i==len(seq)-1):
                triseq = triseq + "C"
            triseq = triseq + tri(s) + " "
	triseq = triseq + "}"

	subprocess.call('cp '+forcefield+' amberscript', shell=True)

	h = open("amberscript", "a")

	h.write("\n"+name+" = sequence "+triseq+"\nsaveoff "+name+" linear.lib\nsavepdb "+name+" linear.pdb\nsaveamberparm "+name+" prmtop rst7\nquit")

	h.close()

	#call Amber Tools tleap
	subprocess.call('tleap -s -f amberscript', shell=True)


