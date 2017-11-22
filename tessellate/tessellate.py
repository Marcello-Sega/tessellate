# -*- coding: utf-8 -*-

"""Tessellate module."""

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def createnodejson_forcrd(id, conformer, puckercoords, nextconformer, ringsize):
    roundedpuckercoords = []
    try:
        for x_ind in puckercoords[1:-2].split(','):
            roundedpuckercoords.append("{0:.2f}".format(float(x_ind)))
    except Exception as e:
        logger.error('%s %s', e, puckercoords)
    jsonobject = {
        'pdbid': id,  # note this could be any id in this case
        'conformer': conformer,
        'puckercoords': roundedpuckercoords,
        'nextconformer': nextconformer,
        'ringsize': ringsize
    }
    return jsonobject, "%s %s %s %s\n" % (conformer, puckercoords, nextconformer, ringsize)

def createnodejson(pdbid, resname, chain, resid, ringorder, conformer, contextconformer, puckercoords, nextconformer, ringsize, macro=False):
    try:
        roundedpuckercoords=[]
        for x_ind in puckercoords:
            roundedpuckercoords.append("{0:.2f}".format(float(x_ind)))
    except Exception as e:
        logger.error('%s %s', e, puckercoords)

    jsonobject = {
        'pdbid': pdbid,
        'resname': resname,
        'chain': chain,
        'resid': resid,
        'ringorder': ringorder,
        'conformer': conformer,
        'contextconformer': contextconformer,
        'puckercoords': roundedpuckercoords,
        'nextconformer': nextconformer,
        'ringsize': ringsize,
        'macro' : macro
    }
    return jsonobject, "%s %s %s %s %s %s %s %s %s %s\n" % (pdbid, resname, chain, resid, ringorder, conformer, contextconformer, puckercoords, nextconformer, ringsize)

def analyse_pucker(inputfile, outputfile="output_of_analyse", output_format="json",
                   working_folder=""):
    pass
    try:
        import os
        import sys
        import time
        import tessellate.utils.pucker as puc
        import json
        import tessellate.utils.helperfunctions as helperfunctions
    except Exception as e:
        print("Error - Cannot import module %s", e)
        exit(1)

    outputfile = ".".join([outputfile, output_format])
    txt = False
    if output_format == "txt":
        txt = True
        outputfile = open(os.path.join(working_folder, outputfile), 'w')
        outputfile.write("tessellate 0.1 txt\n")
        outputfile.write(
            "PUCKER_COORDS CONFORMER ORIG_CONFORMER RING_SIZE\n")
        logger.critical("to be improved, does not match json output at present")
    nodejson = []

    # - does the list of coordinates exist
    inputstream = open(inputfile, 'r')
    for line in inputstream:
        logger.debug('pucker line item %s', line)
        chunked = line.split()
        id = chunked[0]
        ringsize = int((len(chunked) - 1) / 3)
        logger.debug('Ringsize %s', ringsize)
        if ringsize < 5 or ringsize > 8:  # not calculating for these sizes at the moment
            logger.error('Systems containing less than 5 or greater than 8 atoms are not supported. skipping')
            exit(1)  # FIXME!, rather ignore and calculate all others..
        allcoors1 = chunked[1:len(chunked)]
        allcoors = [float(i) for i in allcoors1]
        pobj = puc.Pucker(tuple(allcoors))

        if pobj and pobj.isvalid:
            try:
                thisframeTD = pobj.calculate_triangular_tessellation()
                logger.debug(thisframeTD)
                conformer = pobj.deduce_canonical_conformation()
                nextconformer = pobj.deduce_canonical_conformation(nextguess=True)
                logger.debug('Coordinates are %s %s %s %s : ', str(thisframeTD), str(conformer[0]),
                             str(nextconformer[0]), str(pobj.ringsize))
                node, log = createnodejson_forcrd(id, conformer[0], str(thisframeTD), nextconformer[0], pobj.ringsize)
                logger.info(log)
                if txt:
                    outputfile.write(log)
                nodejson.append(node)

            except Exception as e:
                logger.error('Pucker object valid, but calc, classify etc. failed  %s %s', str(pobj._coords), e)
                raise e
                pass

    if output_format == "json":
        d2 = [key for key in nodejson]
        helperfunctions.write_to_json(d2, os.path.join(working_folder, outputfile))
    elif output_format == "bson":
        d2 = [key for key in nodejson]
        helperfunctions.write_to_bson(d2, os.path.join(working_folder, outputfile))



def analyse_pucker_from_pdbs(pdbinputfilename, ligandinputfilename=None, logfile = 'log_of_analyse.log', outputfile = "output_of_analyse",output_format="json", working_folder="",upload_folder=""):
    try:
        import Bio.PDB as bp
        import tessellate.utils.pucker as puc
        import numpy as np
        import json
        import tessellate.utils.helperfunctions as helperfunctions
        import tessellate.utils.getRing as getRing
        import os
    except Exception as e:
        print("Error - Cannot import module %s", e)
        exit(1)

    #. workaround stdout annoyance, biopdb sometimes uses print
    try:
        import sys
        from io import StringIO
    except Exception as e:
        print("Error - Cannot import module ", e)
        exit(1)

    # code smell - should be able to use a single object , a dict with lists?
    all_pucker_json = helperfunctions.init_all_pucker_dictionary()
    all_macro_pucker_json = helperfunctions.init_all_pucker_dictionary()
    PDBDATA = {}
    nodejson = []

    outputfile = open(os.path.join(working_folder, outputfile), 'w')
    outputfile.write(
        "PDBID RESNAME CHAIN RESID RINGATOMSORDER CONFORMER CONTEXTUAL_CONFORMER ANGULAR_PUCKER_COORDS ORIG_CONFORMER RING_SIZE\n")

    # . read in list of pdbs to read (format is one column of pdb ids
    pdblist = []
    inputfile = open(pdbinputfilename, 'r')
    for line in inputfile:
        logger.debug('Read from pdbnames %s', line)
        pdblist.append(line.strip())

    # . read in ligands with preferred ring ordering (format is name, ringsize, numrings , numrings sets of N atom names
    if ligandinputfilename is None:
        ligand_dict={'3DR': {'num': 1, 'ringids': [("C2'", "C3'", "C4'", "O4'", "C1'")], 'ringsize': 5}, 'AVU': {'num': 2, 'ringids': [("C2'", "C3'", "C4'", "O4'", "C1'"), ('C2R', 'C3R', 'C4R', 'O4R', 'C1R')], 'ringsize': 5}, 'NAG': {'num': 1, 'ringids': [('C3', 'C4', 'C5', 'O5', 'C1', 'C2')], 'ringsize': 6}, 'CTR': {'num': 3, 'ringids': [('C3A', 'C4A', 'C5A', 'O5A', 'C1A', 'C2A'), ('C3B', 'C4B', 'C5B', 'O5B', 'C1B', 'C2B'), ('C3C', 'C4C', 'C5C', 'O5C', 'C1C', 'C2C')], 'ringsize': 6}, 'PSG': {'num': 1, 'ringids': [('C3', 'C4', 'C5', 'O5', 'C1', 'C2')], 'ringsize': 6}, 'MAN': {'num': 1, 'ringids': [('C3', 'C4', 'C5', 'O5', 'C1', 'C2')], 'ringsize': 6}, 'BMA': {'num': 1, 'ringids': [('C3', 'C4', 'C5', 'O5', 'C1', 'C2')], 'ringsize': 6}, 'NDG': {'num': 1, 'ringids': [('C3', 'C4', 'C5', 'O', 'C1', 'C2')], 'ringsize': 6}, 'BGP': {'num': 1, 'ringids': [('C3', 'C4', 'C5', 'O5', 'C1', 'C2')], 'ringsize': 6}, 'G6P': {'num': 1, 'ringids': [('C3', 'C4', 'C5', 'O5', 'C1', 'C2')], 'ringsize': 6}, 'ACR': {'num': 4, 'ringids': [('C3A', 'C4A', 'C5A', 'C7A', 'C1A', 'C2A'), ('C3B', 'C4B', 'C5B', 'O5B', 'C1B', 'C2B'), ('C3C', 'C4C', 'C5C', 'O5C', 'C1C', 'C2C'), ('C3D', 'C4D', 'C5D', 'O5D', 'C1D', 'C2D')], 'ringsize': 6}, 'LAK': {'num': 2, 'ringids': [('C3', 'C4', 'C5', 'O5', 'C1', 'C2'), ("C3'", "C4'", "C5'", "O5'", "C1'", "C2'")], 'ringsize': 6}, 'GAL': {'num': 1, 'ringids': [('C3', 'C4', 'C5', 'O5', 'C1', 'C2')], 'ringsize': 6}, 'BGC': {'num': 1, 'ringids': [('C3', 'C4', 'C5', 'O5', 'C1', 'C2')], 'ringsize': 6}, 'NGA': {'num': 1, 'ringids': [('C3', 'C4', 'C5', 'O5', 'C1', 'C2')], 'ringsize': 6}, 'UPG': {'num': 1, 'ringids': [("C3'", "C4'", "C5'", "O5'", "C1'", "C2'")], 'ringsize': 6}, 'BBA': {'num': 1, 'ringids': [('C1', 'C2', 'C3', 'C', 'C4', 'C5', 'C6')], 'ringsize': 7}, 'H52': {'num': 1, 'ringids': [('N21', 'C22', 'C23', 'N24', 'C25', 'C26', 'C27')], 'ringsize': 7}, '0J0': {'num': 1, 'ringids': [('C15', 'C16', 'C17', 'C18', 'C19', 'C20', 'C21')], 'ringsize': 7}, '13U': {'num': 1, 'ringids': [('C42', 'C43', 'C44', 'C45', 'C46', 'C47', 'C48', 'C49')], 'ringsize': 8}, 'PS9': {'num': 1, 'ringids': [('S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8', 'S9')], 'ringsize': 8}}
    else:
        ligfile = open(ligandinputfilename, 'r')
        ligand_dict = {}
        for line in ligfile:
            chunked = line.split()
            id = chunked[0]
            ringsize = int(chunked[1])
            numrings = int(chunked[2])
            columns = int(3)  # columns in addition to atoms
            if len(chunked) == (columns + int(numrings) * int(ringsize)):
                ligand_dict[id] = {}
                ligand_dict[id]["num"] = numrings
                ligand_dict[id]["ringids"] = []
                ligand_dict[id]["ringsize"] = ringsize
                for i in range(0, numrings):
                    templist = []
                    for j in range(0, ringsize):
                        templist.append(chunked[columns + i * ringsize + int(j)])
                    ligand_dict[id]["ringids"].append(tuple(templist))
                logger.debug('Creation of liganddict %s', ligand_dict[id])
            else:
                logger.error('atoms ids relative to number rings does not match in ligands file %s %s %s %s', chunked,
                          len(chunked), numrings, ringsize)
    logger.debug("Ligand Dict used: %s", ligand_dict)

    # . download pdbs  and if already there will not download
    for pdbid in pdblist:
        logger.debug('Ids in downloads list %s', pdbid)
        pdbl = bp.PDBList()
        pdbl.retrieve_pdb_file(pdbid, file_format="pdb" , pdir=os.path.join(working_folder,"pdb"))

    # . parse pdbs for ligands, when found, calc pucker
    p = bp.PDBParser()

    # .. loop over all pdbs
    for pdbid in pdblist:
        pdbpath = os.path.join(working_folder,"pdb")+"/pdb" + pdbid.lower() + ".ent"
        # else:
        #     pdbpath = os.path.join(upload_folder,pdbid)
        logger.debug('path to pdbids downloaded %s', pdbid)
        structure = p.get_structure(pdbid, pdbpath)
        # .. get all the residues
        res_list = bp.Selection.unfold_entities(structure, 'R')
        # .. loop over the residues
        for resi in res_list:
            SSSR = []
            rname = resi.get_resname()
            # if not an amino acid then look for ring
            aminoacids = ["GLY", "ALA", "SER", "MET", "LYS", "GLU", "PRO", "ASP", "VAL", "PHE", "ASN", "ILE", "TRP",
                          "CYS", "HIS", "LEU", "GLN", "ARG", "TYR", "THR"]
            water = ["HOH"]
            soup = aminoacids + water

            # .. is this residue in the ligands list, calc pucker
            if rname in ligand_dict.keys():
                logger.debug('Ligand %s appears in the ligand dict ', rname)
                # .. get atoms coords
                for nrings in range(0, ligand_dict[rname]["num"]):
                    try:
                        listallcoors = []
                        # .. some pdbs have missing atoms, for this case , check if atoms exist in PDB
                        check_atoms = []
                        for i in resi.get_list():
                            check_atoms.append(i.get_name())
                        missingatomtest = False
                        for atomindex in range(0, ligand_dict[rname]["ringsize"]):
                            if ligand_dict[rname]["ringids"][nrings][atomindex] not in check_atoms:
                                missingatomtest = True
                        if missingatomtest:
                            logger.debug('Missing atoms for %s', rname)
                            pass  # without notifying user !
                        else:

                            for atomindex in range(0, ligand_dict[rname]["ringsize"]):
                                listallcoors = listallcoors + list(
                                    resi[ligand_dict[rname]["ringids"][nrings][atomindex]].get_coord())
                            pobj = puc.Pucker(tuple(listallcoors))
                            if pobj and pobj.isvalid:
                                try:
                                    thisframeTD = pobj.calculate_triangular_tessellation()
                                    conformer = pobj.deduce_canonical_conformation()
                                    nextconformer = pobj.deduce_canonical_conformation(nextguess=True)
                                    pconf = pobj.contextualise_conformer(conformer[0],ligand_dict[rname]["ringids"][nrings])
                                    node, log = createnodejson(pdbid, rname, resi.get_parent().get_id(), resi.get_id()[1], ligand_dict[rname]["ringids"][nrings],conformer[0], pconf, thisframeTD, nextconformer[0], pobj.ringsize)
                                    logger.info(log)
                                    outputfile.write(log)
                                    if not nodejson == [] and node in nodejson:
                                        logger.debug('ENTRY EXISTS : %s %s', rname, resi.get_id()[1])
                                    else:
                                        nodejson.append(node)

                                    ring = ligand_dict[rname]["ringids"][nrings]
                                    #. AVOID ADDING DUPLICATES
                                    pdbdata_entry = dict(chain=resi.get_parent().get_id(), resi=rname, resid=resi.get_id()[1], atoms=ring,
                                                        conformer=conformer[0], TD=thisframeTD)
                                    if pdbid in PDBDATA:
                                        # now check for dups
                                        if pdbdata_entry in PDBDATA[pdbid]:
                                            logger.debug('ENTRY EXISTS : %s %s', rname, resi.get_id()[1])
                                        else:
                                            PDBDATA[pdbid].append(
                                                {"chain" : resi.get_parent().get_id(), "resi": rname, "resid": resi.get_id()[1], "atoms": ring, "conformer": conformer[0],
                                                "TD": thisframeTD})
                                            if conformer[0] in all_pucker_json[pobj.ringsize]:
                                                all_pucker_json[pobj.ringsize][conformer[0]] += 1
                                            else:
                                                all_pucker_json[pobj.ringsize][conformer[0]] = 1
    
                                    else:
                                            if conformer[0] in all_pucker_json[pobj.ringsize]:
                                                all_pucker_json[pobj.ringsize][conformer[0]] += 1
                                            else:
                                                all_pucker_json[pobj.ringsize][conformer[0]] = 1
                                            PDBDATA[pdbid] = [
                                                {"chain" : resi.get_parent().get_id(),"resi": rname, "resid": resi.get_id()[1], "atoms": ring, "conformer": conformer[0],
                                                "TD": thisframeTD}]
                                except Exception as e:
                                    logger.error('In known ligs, Pucker object valid, but calc, classify etc. failed  %s %s', str(pobj._coords), e)
                                    raise e
                            else:
                                logger.error("pobj is None or not valid in ligand ring find %s ", listallcoors)
                    except Exception as e:
                        logger.error("pdb file may be missing coordinates..")
                        raise  # not happy about how I raise this error but OK for now

            # .. Calculate SSSR regardless of whether I have this ligand in the dict or not and then calc pucker
            # .. this may make sense but will cause duplicates ......
            if rname not in soup and len(resi.get_list()) > 5:
                atomlist = []
                if resi.is_disordered():
                    for atom in resi.get_list():  # use get_list instead of unpacked list
                        if atom.is_disordered():
                            list_of_disorder = atom.disordered_get_id_list()
                            # just using the last one for now (whatever that is)
                            selected = list_of_disorder[-1]
                            if atom.disordered_has_id(selected):
                                atom.disordered_select(selected)

                for i in resi.get_list():
                    atomlist.append([i.get_name(), i.get_coord()])
                logger.debug("resi %s atomlist %s", resi, atomlist)
                SSSR = getRing.create_graph_and_find_rings_suite(atomlist)

                if SSSR:
                    for ring in SSSR:
                        nring = SSSR.index(ring)
                        logger.debug('FOUND %i rings in resi %s ', nring+1, rname)
                        alpharing = getRing.getcommonring(ring)
                        if alpharing is not None:
                            ring = alpharing
                        else:  # try see if its common through the common dict
                            for common in getRing.commonrings:
                                if sorted(common) == sorted(ring):
                                    ring = common
                                    break
                        listallcoors = []
                        for atomindex in ring:
                            listallcoors = listallcoors + list(resi[atomindex].get_coord())
                        logger.debug("listallcoors %s", listallcoors)
                        pobj = puc.Pucker(tuple(listallcoors))
                        if pobj and pobj.isvalid:
                            try:
                                thisframeTD = pobj.calculate_triangular_tessellation()
                                conformer = pobj.deduce_canonical_conformation()
                                pconf = pobj.contextualise_conformer(conformer[0], ring)
                                nextconformer = pobj.deduce_canonical_conformation(nextguess=True)
                                node, log = createnodejson(pdbid, rname, resi.get_parent().get_id(), resi.get_id()[1], ring, conformer[0], pconf, thisframeTD, nextconformer[0], pobj.ringsize)
                                logger.info(log)
                                outputfile.write(log)
                                if not nodejson == [] and node in nodejson:
                                    logger.debug('ENTRY EXISTS : %s %s', rname, resi.get_id()[1])
                                else:
                                    nodejson.append(node)
                                #. AVOID ADDING DUPLICATES
                                pdbdata_entry = dict(chain=resi.get_parent().get_id(), resi=rname, resid=resi.get_id()[1], atoms=ring,
                                                     conformer=conformer[0], TD=thisframeTD)
                                if pdbid in PDBDATA:
                                    # now check for dups
                                    if pdbdata_entry in PDBDATA[pdbid]:
                                        logger.debug('ENTRY EXISTS : %s %s', rname, resi.get_id()[1])
                                    else:
                                        PDBDATA[pdbid].append(
                                            {"chain" : resi.get_parent().get_id(), "resi": rname, "resid": resi.get_id()[1], "atoms": ring, "conformer": conformer[0],
                                             "TD": thisframeTD})
                                        if conformer[0] in all_pucker_json[pobj.ringsize]:
                                            all_pucker_json[pobj.ringsize][conformer[0]] += 1
                                        else:
                                            all_pucker_json[pobj.ringsize][conformer[0]] = 1

                                else:
                                        if conformer[0] in all_pucker_json[pobj.ringsize]:
                                            all_pucker_json[pobj.ringsize][conformer[0]] += 1
                                        else:
                                            all_pucker_json[pobj.ringsize][conformer[0]] = 1
                                        PDBDATA[pdbid] = [
                                            {"chain" : resi.get_parent().get_id(),"resi": rname, "resid": resi.get_id()[1], "atoms": ring, "conformer": conformer[0],
                                            "TD": thisframeTD}]
                            except Exception as e:
                                logger.error('In SSSR Pucker object valid, but calc, classify etc. failed  %s %s', str(pobj._coords), e)
                                raise e
                        else:
                            logger.error("pobj is None or not valid in SSSR ring find %s", listallcoors)
                else:
                    logger.debug('%s has no rings', rname)

            #. get all rings in this resi, get com
            macroatomlist = []
            if SSSR:
                for aring in SSSR:
                    ringcoords=[]
                    for ringatom in aring:
                        for itm in resi.get_list():
                            if itm.get_name() == ringatom:
                                ringcoords.append(itm.get_coord())
                    #print aring, np.array(np.add.reduce(ringcoords)/len(ringcoords)), "\n"
                    if len(ringcoords)<9 and len(ringcoords)>4: # ignore too large or too small cycles
                        #print len(ringcoords)
                        macroatomlist.append(["".join(aring), np.array(np.add.reduce(ringcoords)/len(ringcoords))])
                        #macroatomlist.append(["".join(aring), np.array(np.add.reduce(ringcoords))])
                        logger.debug("resi %s rings %s macroatomlist %s", resi, aring, macroatomlist)
                if len(macroatomlist) > 4:  # need at least five cycles to calculate macropucker
                    #print "macroatom ", macroatomlist
                    #import itertools
                    #for a, b in itertools.combinations(macroatomlist, 2):
                    # work out euclidean distance and choose to call this an edge if mineuclid<dist<maxeuclid
                        #print a, b, np.linalg.norm(a[1] - b[1])

                    macroSSSR = getRing.create_graph_and_find_rings_suite(macroatomlist,maxeuclid=6.0)
                    if macroSSSR:
                        #print "mS ", macroSSSR
                        for ring in macroSSSR:
                            nring = macroSSSR.index(ring)
                            logger.debug('FOUND %i macro rings in resi %s ', nring+1, rname)
                            alpharing = getRing.getcommonring(ring)
                            if alpharing is not None:
                                ring = alpharing
                            else:  # try see if its common through the common dict
                                for common in getRing.commonrings:
                                    if sorted(common) == sorted(ring):
                                        ring = common
                                        break
                            listallcoors = []
                            #print macroatomlist
                            for atoms in ring:
                                listallcoors.extend(list((list(x[1]) for x in macroatomlist if x[0] in atoms)))
                            # now flatten the list
                            listallcoors = [y for x in listallcoors for y in x]

                            logger.debug("macro listallcoors %s", listallcoors)
                            pobj = puc.Pucker(tuple(listallcoors))
                            if pobj and pobj.isvalid:
                                try:
                                    thisframeTD = pobj.calculate_triangular_tessellation()
                                    conformer = pobj.deduce_canonical_conformation()
                                    pconf = pobj.contextualise_conformer(conformer[0], ring)
                                    nextconformer = pobj.deduce_canonical_conformation(nextguess=True)
                                    logger.debug("Macrocycles %s %s %s %s", thisframeTD, conformer, pconf, nextconformer)
                                    node, log = createnodejson(pdbid, rname, resi.get_parent().get_id(), resi.get_id()[1], ring, conformer[0], pconf, thisframeTD, nextconformer[0], pobj.ringsize, True)
                                    logger.info(log)
                                    outputfile.write(log)
                                    if not nodejson == [] and node in nodejson:
                                        logger.debug('ENTRY EXISTS : %s %s', rname, resi.get_id()[1])
                                    else:
                                        nodejson.append(node)
                                    #. AVOID ADDING DUPLICATES
                                    pdbdata_entry = dict(chain=resi.get_parent().get_id(), resi=rname, resid=resi.get_id()[1], atoms=ring,
                                                     conformer=conformer[0], TD=thisframeTD)
                                    if pdbid in PDBDATA:
                                        # now check for dups
                                        if pdbdata_entry in PDBDATA[pdbid]:
                                            logger.debug('ENTRY EXISTS : %s %s', rname, resi.get_id()[1])
                                        else:
                                            PDBDATA[pdbid].append(
                                                {"chain":resi.get_parent().get_id(), "resi": rname, "resid": resi.get_id()[1], "atoms": ring, "conformer": conformer[0],
                                                "TD": thisframeTD})
                                            if conformer[0] in all_macro_pucker_json[pobj.ringsize]:
                                                all_macro_pucker_json[pobj.ringsize][conformer[0]] += 1
                                            else:
                                                all_macro_pucker_json[pobj.ringsize][conformer[0]] = 1
    
                                    else:
                                            if conformer[0] in all_macro_pucker_json[pobj.ringsize]:
                                                all_macro_pucker_json[pobj.ringsize][conformer[0]] += 1
                                            else:
                                                all_macro_pucker_json[pobj.ringsize][conformer[0]] = 1
                                            PDBDATA[pdbid] = [
                                                {"chain":resi.get_parent().get_id(),"resi": rname, "resid": resi.get_id()[1], "atoms": ring, "conformer": conformer[0],
                                                "TD": thisframeTD}]
                                except Exception as e:
                                    logger.error('In macrocyc, Pucker object valid, but calc, classify etc. failed  %s %s', str(pobj._coords), e)
                                    pass
                            else:
                                logger.error("pobj is None or not valid in macrocyc %s",listallcoors)
                    else:
                        logger.debug('%s has no rings', rname)



    # find info on all rings in a pdb. PDBDATA has this information
    #for keys,items in PDBDATA.items():
    #    if len(items)>4:
    #        for kitem in items:
    #            print kitem["coors"]
                # com   center = np.add.reduce(atoms[0:noa]) / noa
                #    logger.debug('pdbdata', PDBDATA)
    # loop over PDBDATA
    # for each item if it has a dict >=5 then it worth looking at it.
    # for each item in dict. calc c.o.m.,
    # create edges between items if 1.5 < dist < 6 (actually should check connectivity, but not yet

    pucsummary = open(os.path.join(working_folder, 'pucker_summary.csv'), 'w')
    pucsummary.write("size,conformer,count\n")
    for key in all_pucker_json[5]:
        pucsummary.write(",".join(("FIVE", key, str(all_pucker_json[5][key]), "\n")))
        try:
            all_pucker_json["five"].append({"label": key, "macrovalue": float(all_macro_pucker_json[5][key]), "value": float(all_pucker_json[5][key]), "id": key, "weight": 1,"order": helperfunctions.getorder(5,key), "color_aster":helperfunctions.getcolor(5,key)})
        except:
            all_pucker_json["five"] = [{"label": key, "macrovalue": float(all_macro_pucker_json[5][key]), "value": float(all_pucker_json[5][key]), "id": key, "weight": 1,"order": helperfunctions.getorder(5,key), "color_aster":helperfunctions.getcolor(5,key)}]

    for key in all_pucker_json[6]:
        pucsummary.write(",".join(("SIX", key, str(all_pucker_json[6][key]), "\n")))
        try:
            #all_pucker_json["six"].append({"label": key, "value": float(all_pucker_json[6][key])})
            all_pucker_json["six"].append({"label": key, "macrovalue": float(all_macro_pucker_json[6][key]), "value": float(all_pucker_json[6][key]), "id": key, "weight": 1,"order": helperfunctions.getorder(6,key), "color_aster":helperfunctions.getcolor(6,key)})
        except:
            all_pucker_json["six"] = [{"label": key, "macrovalue": float(all_macro_pucker_json[6][key]), "value": float(all_pucker_json[6][key]), "id": key, "weight": 1,"order": helperfunctions.getorder(6,key), "color_aster":helperfunctions.getcolor(6,key)}]
    for key in all_pucker_json[7]:
        pucsummary.write(",".join(("SEVEN", key, str(all_pucker_json[7][key]), "\n")))
        try:
            #all_pucker_json["seven"].append({"label": key, "value": float(all_pucker_json[7][key])})
            all_pucker_json["seven"].append({"label": key, "macrovalue": float(all_macro_pucker_json[7][key]), "value": float(all_pucker_json[7][key]), "id": key, "weight": 1,"order": helperfunctions.getorder(7,key), "color_aster":helperfunctions.getcolor(7,key)})
        except:
            #all_pucker_json["seven"] = [{"label": key, "value": float(all_pucker_json[7][key])}]
            all_pucker_json["seven"] = [{"label": key, "macrovalue": float(all_macro_pucker_json[7][key]), "value": float(all_pucker_json[7][key]), "id": key, "weight": 1,"order": helperfunctions.getorder(7,key), "color_aster":helperfunctions.getcolor(7,key)}]
    for key in all_pucker_json[8]:
        pucsummary.write(",".join(("EIGHT", key, str(all_pucker_json[8][key]), "\n")))
        try:
            #all_pucker_json["eight"].append({"label": key, "value": float(all_pucker_json[8][key])})
            all_pucker_json["eight"].append({"label": key, "macrovalue": float(all_macro_pucker_json[8][key]), "value": float(all_pucker_json[8][key]), "id": key, "weight": 1,"order": helperfunctions.getorder(8,key), "color_aster":helperfunctions.getcolor(8,key)})
        except:
            #all_pucker_json["eight"] = [{"label": key, "value": float(all_pucker_json[8][key])}]
            all_pucker_json["eight"] = [{"label": key, "macrovalue": float(all_macro_pucker_json[8][key]), "value": float(all_pucker_json[8][key]), "id": key, "weight": 1,"order": helperfunctions.getorder(8,key), "color_aster":helperfunctions.getcolor(8,key)}]
    pucsummary.close()
    # <> dump all the pucker stats as json files
    d2 = [key for key in all_pucker_json["five"]]
    #d2 = {"data": [key for key in nodejson]}
    helperfunctions.write_to_json(d2, os.path.join(working_folder, 'five.json'))
    #d2 = [key for key in all_pucker_json["six"]]
    d2 = [key for key in sorted(all_pucker_json["six"], key=lambda dist: dist["order"] )]
    helperfunctions.write_to_json(d2, os.path.join(working_folder, 'six.json'))
    #d2 = [key for key in all_pucker_json["seven"]]
    d2 = [key for key in sorted(all_pucker_json["seven"], key=lambda dist: dist["order"] )]
    helperfunctions.write_to_json(d2, os.path.join(working_folder, 'seven.json'))
    #d2 = [key for key in all_pucker_json["eight"]]
    d2 = [key for key in sorted(all_pucker_json["eight"], key=lambda dist: dist["order"] )]
    helperfunctions.write_to_json(d2, os.path.join(working_folder, 'eight.json'))

    # <> dump pucker stats out to be used in discrete bar charts, if value is not a float then graph doesn't work properly "1" -> 1.0
    d2 = [{'key': 'five cycles', "color": "#d67777", 'values': [key for key in all_pucker_json["five"]]}]
    helperfunctions.write_to_json(d2, os.path.join(working_folder, 'five_bar.json'))
    d2 = [{'key': 'six cycles', "color": "#d67777", 'values': [key for key in all_pucker_json["six"]]}]
    #d2 = [{ 'key' : 'six cycles', "color": "#d67777", 'values' : [sorted([(key,value) for (key,value) in all_pucker_json["six"]])]} ]
    helperfunctions.write_to_json(d2, os.path.join(working_folder, 'six_bar.json'))
    d2 = [{'key': 'seven cycles', "color": "#d67777", 'values': [key for key in all_pucker_json["seven"]]}]
    helperfunctions.write_to_json(d2, os.path.join(working_folder, 'seven_bar.json'))
    d2 = [{'key': 'eight cycles', "color": "#d67777", 'values': [key for key in all_pucker_json["eight"]]}]
    helperfunctions.write_to_json(d2, os.path.join(working_folder, 'eight_bar.json'))

    d = {"name": "PDB", "children": [{'name': key, "children": value} for key, value in PDBDATA.items()]}
    helperfunctions.write_to_json(d, os.path.join(working_folder, 'pucker_flare.json'))

    d2 = {"five": [key for key in sorted(all_pucker_json["five"], key=lambda dist: dist["order"] )],"six": [key for key in sorted(all_pucker_json["six"], key=lambda dist: dist["order"] )],"seven": [key for key in sorted(all_pucker_json["seven"], key=lambda dist: dist["order"] )],"eight": [key for key in sorted(all_pucker_json["eight"], key=lambda dist: dist["order"] )]}
    helperfunctions.write_to_json(d2, os.path.join(working_folder, 'aster.json'))

    # JSONTABLEDATA
    #d2 = {"data":[{{k:i}for k,i in key.items()} for key in nodejson]}
    d2 = [key for key in nodejson]
    helperfunctions.write_to_json(d2, os.path.join(working_folder, 'pucker_table.json'))
    print("puckertable:", d2)
    print( os.getcwd())
    inputfile.close()
    outputfile.close()
    logger.debug("all_pucker_json %s", all_pucker_json)
    logger.debug("PDBDATA %s", PDBDATA)
    logger.debug("nodejson %s", nodejson)
    return

if __name__ == "__main__":
    try:
        import sys
    except Exception as e:
        print("Error - Cannot import module ", e)
        exit(1)
    analyse_pucker_from_pdbs(sys.argv[1], sys.argv[2], sys.argv[3])

