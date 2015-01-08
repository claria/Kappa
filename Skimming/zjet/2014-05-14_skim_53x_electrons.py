import FWCore.ParameterSet.Config as cms


def getBaseConfig(globaltag, testfile="", maxevents=0, datatype='data'):
    """Default config for Z+jet skims with Kappa

       This is used in a cmssw config file via:
       import skim_base
       process = skim_base.getBaseConfig('START53_V12', "testfile.root")
    """
    # print the globalt tag and datatype for testing or by grid-control ---------
    isData = (datatype == 'data')
    isMC = not isData
    print "GT:", globaltag, "| TYPE:", datatype, "| maxevents:", maxevents, "| file:", testfile

    # Basic process setup -----------------------------------------------------
    process = cms.Process('kappaSkim')
    process.maxEvents = cms.untracked.PSet(
        input = cms.untracked.int32(maxevents))
    process.source = cms.Source('PoolSource',
        fileNames = cms.untracked.vstring(testfile))

    # Includes + Global Tag ---------------------------------------------------
    process.load('FWCore.MessageService.MessageLogger_cfi')
    process.load('Configuration.StandardSequences.Services_cff')
    process.load('Configuration.StandardSequences.MagneticField_38T_cff')
    process.load('Configuration.Geometry.GeometryIdeal_cff')
    process.load('Configuration.Geometry.GeometryPilot2_cff')
    process.load('TrackPropagation.SteppingHelixPropagator.SteppingHelixPropagatorAny_cfi')
    process.load('TrackPropagation.SteppingHelixPropagator.SteppingHelixPropagatorAlong_cfi')
    process.load('TrackPropagation.SteppingHelixPropagator.SteppingHelixPropagatorOpposite_cfi')
    process.load('RecoMuon.DetLayers.muonDetLayerGeometry_cfi')
    process.load('Configuration.StandardSequences.FrontierConditions_GlobalTag_cff')
    process.load('Configuration.StandardSequences.Reconstruction_cff')
    process.GlobalTag.globaltag = globaltag + '::All'

    # Reduce amount of messages -----------------------------------------------
    process.MessageLogger.default = cms.untracked.PSet(
        ERROR = cms.untracked.PSet(limit = cms.untracked.int32(5)))
    process.MessageLogger.cerr.FwkReport.reportEvery = 40

    # Electrons ---------------------------------------------------------------
    process.load("Kappa.Producers.KElectrons_cff")
    
    # momentum corrections
    process.load('EgammaAnalysis.ElectronTools.electronRegressionEnergyProducer_cfi')
    process.eleRegressionEnergy.inputElectronsTag = cms.InputTag('patElectrons')
    process.eleRegressionEnergy.inputCollectionType = cms.uint32(1)

    process.load("Configuration.StandardSequences.Services_cff")
    process.RandomNumberGeneratorService = cms.Service("RandomNumberGeneratorService",
            calibratedPatElectrons = cms.PSet(
                initialSeed = cms.untracked.uint32(1),
                engineName = cms.untracked.string('TRandom3')
            ),
    )

    # calibrate pat electrons
    process.load("EgammaAnalysis.ElectronTools.calibratedPatElectrons_cfi")
    if isData:
        inputDataset =  "22Jan2013ReReco"
    else:
        inputDataset =  "Summer12_DR53X_HCP2012"
    process.calibratedPatElectrons.inputDataset = cms.string(inputDataset)
    process.calibratedPatElectrons.isMC = cms.bool(isMC)


    ## for cutbased ID
    from CommonTools.ParticleFlow.Tools.pfIsolation import setupPFElectronIso, setupPFMuonIso
    process.calibeleIsoSequence = setupPFElectronIso(process, 'calibratedPatElectrons', "PFIsoCal")
    process.eleIsoSequence = setupPFElectronIso(process, 'patElectrons')
    process.pfiso = cms.Sequence(process.pfParticleSelectionSequence
        + process.eleIsoSequence + process.calibeleIsoSequence 
        )

    # rho for e isolation
    from RecoJets.JetProducers.kt4PFJets_cfi import kt4PFJets
    process.kt6PFJetsForIsolation = kt4PFJets.clone( rParam = 0.6, doRhoFastjet = True )
    process.kt6PFJetsForIsolation.Rho_EtaMax = cms.double(2.5)

    process.electrons = cms.Path(
        process.makeKappaElectrons *
        process.eleRegressionEnergy*
        process.calibratedPatElectrons * 
        process.pfiso *
        process.kt6PFJetsForIsolation
    )


    # Create good primary vertices to be used for PF association --------------
    from PhysicsTools.SelectorUtils.pvSelector_cfi import pvSelector
    process.goodOfflinePrimaryVertices = cms.EDFilter("PrimaryVertexObjectFilter",
        filterParams = pvSelector.clone(minNdof = cms.double(4.0), maxZ = cms.double(24.0)),
        src=cms.InputTag('offlinePrimaryVertices')
    )
    process.ak5PFJets.srcPVs = cms.InputTag('goodOfflinePrimaryVertices')
    process.kt4PFJets.srcPVs = cms.InputTag('goodOfflinePrimaryVertices')
    process.kt6PFJets.srcPVs = cms.InputTag('goodOfflinePrimaryVertices')


    # CHS Jets with the NoPU sequence -----------------------------------------
    process.load('CommonTools.ParticleFlow.PFBRECO_cff')
    process.pfPileUp.Vertices = cms.InputTag('goodOfflinePrimaryVertices')
    process.pfPileUp.checkClosestZVertex = cms.bool(False)
    process.pfCHS = cms.Path(process.goodOfflinePrimaryVertices * process.PFBRECO)
    process.ak5PFJetsCHS = process.ak5PFJets.clone(src = cms.InputTag('pfNoPileUp'))
    process.kt4PFJetsCHS = process.kt4PFJets.clone(src = cms.InputTag('pfNoPileUp'))
    process.kt6PFJetsCHS = process.kt6PFJets.clone(src = cms.InputTag('pfNoPileUp'))
    
    # Gen Jets without neutrinos ----------------------------------------------
    if isMC:
        process.load('RecoJets.JetProducers.ak5GenJets_cfi')
        process.NoNuGenJets = cms.Path(process.genParticlesForJetsNoNu *
            process.genParticlesForJets *
            process.ak5GenJetsNoNu * 
            process.kt4GenJetsNoNu * process.kt4GenJets *
            process.kt6GenJetsNoNu * process.kt6GenJets
        )

    # Path to Redo all Jets ---------------------------------------------------
    process.jetsRedo = cms.Path(
        process.ak5PFJets * process.kt4PFJets * process.kt6PFJets *
        process.ak5PFJetsCHS * process.kt4PFJetsCHS * process.kt6PFJetsCHS
    )

    # QG TAGGER ----------------------------------------------------------------
    process.load('QuarkGluonTagger.EightTeV.QGTagger_RecoJets_cff')
    process.QGTagger.srcJets = cms.InputTag("ak5PFJets")

    process.AK5PFJetsQGTagger = process.QGTagger
    process.AK5PFJetsCHSQGTagger = process.QGTagger.clone(
        srcJets = cms.InputTag("ak5PFJetsCHS"),
        useCHS = cms.untracked.bool(True))

    process.QGTagging = cms.Path(process.QuarkGluonTagger
        * process.AK5PFJetsQGTagger * process.AK5PFJetsCHSQGTagger)

    # B-Tagging ----------------------------------------------------------------
    # b-tagging general configuration
    process.load("RecoJets.JetAssociationProducers.ic5JetTracksAssociatorAtVertex_cfi")
    process.load("RecoBTag.Configuration.RecoBTag_cff")

    ### AK5
    # create a ak5PF jets and tracks association
    process.ak5PFJetTracksAssociatorAtVertex = process.ic5JetTracksAssociatorAtVertex.clone()
    process.ak5PFJetTracksAssociatorAtVertex.jets = "ak5PFJets"
    process.ak5PFJetTracksAssociatorAtVertex.tracks = "generalTracks"

    process.ak5PFImpactParameterTagInfos = process.impactParameterTagInfos.clone()
    process.ak5PFImpactParameterTagInfos.jetTracks = "ak5PFJetTracksAssociatorAtVertex"

    # secondary vertex b-tag
    process.ak5PFSecondaryVertexTagInfos = process.secondaryVertexTagInfos.clone()
    process.ak5PFSecondaryVertexTagInfos.trackIPTagInfos = "ak5PFImpactParameterTagInfos"
    process.ak5PFSimpleSecondaryVertexBJetTags = process.simpleSecondaryVertexBJetTags.clone()
    process.ak5PFSimpleSecondaryVertexBJetTags.tagInfos = cms.VInputTag(cms.InputTag("ak5PFSecondaryVertexTagInfos"))
    process.ak5PFCombinedSecondaryVertexBJetTags = process.combinedSecondaryVertexBJetTags.clone()
    process.ak5PFCombinedSecondaryVertexBJetTags.tagInfos = cms.VInputTag(
        cms.InputTag("ak5PFImpactParameterTagInfos"),
        cms.InputTag("ak5PFSecondaryVertexTagInfos"))
    process.ak5PFCombinedSecondaryVertexMVABJetTags = process.combinedSecondaryVertexMVABJetTags.clone()
    process.ak5PFCombinedSecondaryVertexMVABJetTags.tagInfos = cms.VInputTag(
        cms.InputTag("ak5PFImpactParameterTagInfos"),
        cms.InputTag("ak5PFSecondaryVertexTagInfos"))

    # sequence for AK5 b-tagging
    process.ak5PFJetBtagging = cms.Sequence(process.ak5PFJetTracksAssociatorAtVertex
        * process.ak5PFImpactParameterTagInfos
        * process.ak5PFSecondaryVertexTagInfos
        * process.ak5PFSecondaryVertexTagInfos
        * (process.ak5PFSimpleSecondaryVertexBJetTags + process.ak5PFCombinedSecondaryVertexBJetTags + process.ak5PFCombinedSecondaryVertexMVABJetTags))


    ### AK5 CHS
    # create a ak5PFCHS jets and tracks association
    process.ak5PFCHSJetTracksAssociatorAtVertex = process.ic5JetTracksAssociatorAtVertex.clone()
    process.ak5PFCHSJetTracksAssociatorAtVertex.jets = "ak5PFJetsCHS"
    process.ak5PFCHSJetTracksAssociatorAtVertex.tracks = "generalTracks"

    process.ak5PFCHSImpactParameterTagInfos = process.impactParameterTagInfos.clone()
    process.ak5PFCHSImpactParameterTagInfos.jetTracks = "ak5PFCHSJetTracksAssociatorAtVertex"

    # secondary vertex b-tag
    process.ak5PFCHSSecondaryVertexTagInfos = process.secondaryVertexTagInfos.clone()
    process.ak5PFCHSSecondaryVertexTagInfos.trackIPTagInfos = "ak5PFCHSImpactParameterTagInfos"
    process.ak5PFCHSSimpleSecondaryVertexBJetTags = process.simpleSecondaryVertexBJetTags.clone()
    process.ak5PFCHSSimpleSecondaryVertexBJetTags.tagInfos = cms.VInputTag(cms.InputTag("ak5PFCHSSecondaryVertexTagInfos"))
    process.ak5PFCHSCombinedSecondaryVertexBJetTags = process.combinedSecondaryVertexBJetTags.clone()
    process.ak5PFCHSCombinedSecondaryVertexBJetTags.tagInfos = cms.VInputTag(
        cms.InputTag("ak5PFCHSImpactParameterTagInfos"),
        cms.InputTag("ak5PFCHSSecondaryVertexTagInfos"))
    process.ak5PFCHSCombinedSecondaryVertexMVABJetTags = process.combinedSecondaryVertexMVABJetTags.clone()
    process.ak5PFCHSCombinedSecondaryVertexMVABJetTags.tagInfos = cms.VInputTag(
        cms.InputTag("ak5PFCHSImpactParameterTagInfos"),
        cms.InputTag("ak5PFCHSSecondaryVertexTagInfos"))

    # sequence for AK5CHS b-tagging
    process.ak5PFCHSJetBtagging = cms.Sequence(process.ak5PFCHSJetTracksAssociatorAtVertex
        * process.ak5PFCHSImpactParameterTagInfos
        * process.ak5PFCHSSecondaryVertexTagInfos
        * process.ak5PFCHSSecondaryVertexTagInfos
        * (process.ak5PFCHSSimpleSecondaryVertexBJetTags + process.ak5PFCHSCombinedSecondaryVertexBJetTags + process.ak5PFCHSCombinedSecondaryVertexMVABJetTags))


    # Add the modules for all the jet collections to the path
    process.BTagging = cms.Path(
        process.ak5PFJetBtagging
        * process.ak5PFCHSJetBtagging
    )

    # PU jet ID ---------------------------------------------------------------
    process.load("RecoJets.JetProducers.PileupJetID_cfi")

    # AK5
    process.ak5PFPuJetId = process.pileupJetIdProducer.clone(
       jets = cms.InputTag("ak5PFJets"),
       applyJec = cms.bool(True),
       inputIsCorrected = cms.bool(False),
       residualsTxt     = cms.FileInPath("RecoMET/METPUSubtraction/data/dummy.txt"),
    )

    process.ak5PFPuJetMva = process.pileupJetIdProducer.clone(
       jets = cms.InputTag("ak5PFJets"),
       jetids = cms.InputTag("ak5PFPuJetId"),
       applyJec = cms.bool(True),
       inputIsCorrected = cms.bool(False),
       residualsTxt     = cms.FileInPath("RecoMET/METPUSubtraction/data/dummy.txt"),
    )
    # AK5 CHS
    process.ak5PFCHSPuJetId = process.pileupJetIdProducerChs.clone(
       jets = cms.InputTag("ak5PFJetsCHS"),
       applyJec = cms.bool(True),
       inputIsCorrected = cms.bool(False),
       residualsTxt     = cms.FileInPath("RecoMET/METPUSubtraction/data/dummy.txt"),
    )

    process.ak5PFCHSPuJetMva = process.pileupJetIdProducerChs.clone(
       jets = cms.InputTag("ak5PFJetsCHS"),
       jetids = cms.InputTag("ak5PFCHSPuJetId"),
       applyJec = cms.bool(True),
       inputIsCorrected = cms.bool(False),
       residualsTxt     = cms.FileInPath("RecoMET/METPUSubtraction/data/dummy.txt"),
    )


    process.PUJetID = cms.Path(process.ak5PFPuJetId * process.ak5PFPuJetMva
                        * process.ak5PFCHSPuJetId * process.ak5PFCHSPuJetMva)

    # MET filters -------------------------------------------------------------
    process.load('RecoMET.METFilters.ecalLaserCorrFilter_cfi')
    # Create good vertices for the trackingFailure MET filter
    process.goodVertices = cms.EDFilter("VertexSelector",
        filter = cms.bool(False),
        src = cms.InputTag("offlinePrimaryVertices"),
        cut = cms.string("!isFake && ndof > 4 && abs(z) <= 24 && position.rho < 2"),
    )
    # The good primary vertex filter for other MET filters
    process.primaryVertexFilter = cms.EDFilter("VertexSelector",
        filter = cms.bool(True),
        src = cms.InputTag("offlinePrimaryVertices"),
        cut = cms.string("!isFake && ndof > 4 && abs(z) <= 24 && position.Rho <= 2"),
    )
    process.noscraping = cms.EDFilter("FilterOutScraping",
        applyfilter = cms.untracked.bool(True),
        debugOn = cms.untracked.bool(False),
        numtrack = cms.untracked.uint32(10),
        thresh = cms.untracked.double(0.25)
    )
    process.load('CommonTools.RecoAlgos.HBHENoiseFilter_cfi')
    process.load('RecoMET.METAnalyzers.CSCHaloFilter_cfi')
    process.load('RecoMET.METFilters.hcalLaserEventFilter_cfi')
    process.hcalLaserEventFilter.vetoByRunEventNumber = cms.untracked.bool(False)
    process.hcalLaserEventFilter.vetoByHBHEOccupancy = cms.untracked.bool(True)
    process.load('RecoMET.METFilters.EcalDeadCellTriggerPrimitiveFilter_cfi')
    process.EcalDeadCellTriggerPrimitiveFilter.tpDigiCollection = cms.InputTag("ecalTPSkimNA")
    process.load('RecoMET.METFilters.EcalDeadCellBoundaryEnergyFilter_cfi')
    process.load('RecoMET.METFilters.eeBadScFilter_cfi')
    process.load('RecoMET.METFilters.eeNoiseFilter_cfi')
    process.load('RecoMET.METFilters.ecalLaserCorrFilter_cfi')
    process.load('RecoMET.METFilters.trackingFailureFilter_cfi')
    process.load('RecoMET.METFilters.inconsistentMuonPFCandidateFilter_cfi')
    process.load('RecoMET.METFilters.greedyMuonPFCandidateFilter_cfi')

    process.hcalLaserEventFilter.taggingMode = cms.bool(True)
    process.EcalDeadCellTriggerPrimitiveFilter.taggingMode = cms.bool(True)
    process.EcalDeadCellBoundaryEnergyFilter.taggingMode = cms.bool(True)
    process.trackingFailureFilter.taggingMode = cms.bool(True)
    process.eeBadScFilter.taggingMode = cms.bool(True)
    process.eeNoiseFilter.taggingMode = cms.bool(True)
    process.ecalLaserCorrFilter.taggingMode = cms.bool(True)
    process.trackingFailureFilter.taggingMode = cms.bool(True)
    process.inconsistentMuonPFCandidateFilter.taggingMode = cms.bool(True)
    process.greedyMuonPFCandidateFilter.taggingMode = cms.bool(True)
    process.beamScrapingFilter = process.inconsistentMuonPFCandidateFilter.clone(
        ptMin = cms.double(5000.0)
    )
    process.hcalNoiseFilter = process.beamScrapingFilter.clone()
    process.beamHaloFilter = process.beamScrapingFilter.clone()
    process.filtersSeq = cms.Sequence(
        process.primaryVertexFilter *
        process.hcalLaserEventFilter +
        process.EcalDeadCellTriggerPrimitiveFilter +
        process.EcalDeadCellBoundaryEnergyFilter +
        process.eeBadScFilter +
        process.eeNoiseFilter +
        process.ecalLaserCorrFilter +
        process.goodVertices * process.trackingFailureFilter +
        process.inconsistentMuonPFCandidateFilter +
        process.greedyMuonPFCandidateFilter +
        process.noscraping * process.beamScrapingFilter +
        process.HBHENoiseFilter * process.hcalNoiseFilter +
        process.CSCTightHaloFilter * process.beamHaloFilter
    )
    process.metFilters = cms.Path(process.filtersSeq)

    # MET correction ----------------------------------------------------------
    process.load("JetMETCorrections.Type1MET.pfMETCorrections_cff")
    process.pfchsMETcorr.src = cms.InputTag('goodOfflinePrimaryVertices')
    # Type-0
    process.pfMETCHS = process.pfType1CorrectedMet.clone(
        applyType1Corrections = cms.bool(False),
        applyType0Corrections = cms.bool(True)
    )
    # MET Path
    process.metCorrections = cms.Path(
            process.producePFMETCorrections * process.pfMETCHS
    )
    
    # Configure tuple generation ----------------------------------------------
    process.load('Kappa.Producers.KTuple_cff')
    process.kappatuple = cms.EDAnalyzer('KTuple',
        process.kappaTupleDefaultsBlock,
        outputFile = cms.string("skim_%s.root" % datatype),
        PFTaggedJets = cms.PSet(
            process.kappaNoCut,
            process.kappaNoRegEx,
            taggers = cms.vstring(
                "QGlikelihood", "QGmlp",
                "CombinedSecondaryVertexBJetTags", "CombinedSecondaryVertexMVABJetTags",
                "puJetIDFullLoose", "puJetIDFullMedium", "puJetIDFullTight",
                "puJetIDCutbasedLoose", "puJetIDCutbasedMedium", "puJetIDCutbasedTight",
                "puJetIDMET"
            ),
            AK5PFTaggedJets = cms.PSet(
                src = cms.InputTag("ak5PFJets"),
                QGtagger = cms.InputTag("AK5PFJetsQGTagger"),
                Btagger = cms.InputTag("ak5PF"),
                PUJetID = cms.InputTag("ak5PFPuJetMva"),
                PUJetID_full = cms.InputTag("full"),
            ),
            AK5PFTaggedJetsCHS = cms.PSet(
                src = cms.InputTag("ak5PFJetsCHS"),
                QGtagger = cms.InputTag("AK5PFJetsCHSQGTagger"),
                Btagger = cms.InputTag("ak5PFCHS"),
                PUJetID = cms.InputTag("ak5PFCHSPuJetMva"),
                PUJetID_full = cms.InputTag("full"),
            ),
        ),
    )

    process.kappatuple.verbose = cms.int32(0)
    process.kappatuple.active = cms.vstring(
        'LV', 'Electrons', 'TrackSummary', 'VertexSummary', 'BeamSpot',
        'JetArea', 'PFMET', 
        'FilterSummary', 
        'PFTaggedJets',
        
    )
    if isData:
        additional_actives = ['DataMetadata']
    else:
        additional_actives = ['GenMetadata', 'GenParticles', 'LHE']
    for active in additional_actives:
        process.kappatuple.active.append(active)

    process.kappatuple.LV.blacklist += cms.vstring("AK5TrackJets", ".*KT.*")
    process.kappatuple.PFMET.blacklist = cms.vstring("pfType1.*CorrectedMet")

    process.kappatuple.Metadata.hltWhitelist  += cms.vstring(
        "^HLT_(Double)?E([0-9]+)(_v[[:digit:]]+)?$",  # matches 'HLT_DoubleMu7_v8' etc.
        "^HLT_(Double)?Electron([0-9]+)(_v[[:digit:]]+)?$",
        "^HLT_(Single)?Electron([0-9]+)(_v[[:digit:]]+)?$",
        "HLT_Ele17.*",
        "HLT_DoubleEle.*",
    )

    process.kappatuple.Metadata.hltBlacklist  += cms.vstring(
        "^HLT_(Double)?Mu([0-9]+)_(Double)?Mu([0-9]+)(_v[[:digit:]]+)?$",  # matches 'HLT_Mu17_Mu8_v7' etc.
    )

    process.pathKappa = cms.Path(
        process.kappatuple
    )


    # Process schedule --------------------------------------------------------
    process.schedule = cms.Schedule(
        process.metFilters,
        process.pfCHS,
        process.jetsRedo,
        process.BTagging,
        process.QGTagging,
        process.PUJetID,
        process.metCorrections,
        process.electrons,
        process.pathKappa,
    )
    if isMC:
        process.schedule.insert(0, process.NoNuGenJets)

    return process


def addOutputModule(process, filename="test_out.root"):
    """Additional output file for testing.

       Do not use for a full skim, only for a few 100 events.
       Usage in cmssw config: process = base.addOutputModule(process)
    """
    process.Out = cms.OutputModule("PoolOutputModule",
         fileName = cms.untracked.string(filename)
    )
    process.end = cms.EndPath(process.Out)
    process.schedule.append(process.end)
    return process

if __name__ == "__main__":
    process = getBaseConfig('@GLOBALTAG@', datatype='@TYPE@')