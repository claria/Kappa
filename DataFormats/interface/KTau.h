#ifndef KAPPA_TAU_H
#define KAPPA_TAU_H

#include "KBasic.h"
#include "KMetadata.h"

struct KDataTau : KDataLV
{
	unsigned long long discr;

	char charge;
};
typedef std::vector<KDataTau> KDataTaus;

struct KDataCaloTau : KDataTau
{
	bool hasID(const std::string& name, const KLumiMetadata * lumimetadata) const
	{
		for(size_t i = 0; i < lumimetadata->discrTau.size(); ++i)
			if(lumimetadata->discrTau[i] == name)
				return (discr & (1ull << i)) != 0;
		return false; // Named discriminator does not exist
	}
};
typedef std::vector<KDataCaloTau> KDataCaloTaus;

struct KDataPFTau : KDataTau
{
	float emFraction;

	int cntSignalChargedHadrCands, cntSignalGammaCands, cntSignalNeutrHadrCands, cntSignalCands;

	RMDataLV leadTrack;
	RMDataLV leadChargedHadrTrack;
	RMDataLV leadNeutralTrack;

	KDataVertex vertex;

	//bool longLived
	int cntSignalTracks;

	bool hasID(const std::string& name, const KLumiMetadata * lumimetadata) const
	{
		for(size_t i = 0; i < lumimetadata->discrTauPF.size(); ++i)
			if(lumimetadata->discrTauPF[i] == name)
				return (discr & (1ull << i)) != 0;
		return false; // Named discriminator does not exist
	}
};
typedef std::vector<KDataPFTau> KDataPFTaus;

struct KDataGenTau : KGenParticle
{
	RMDataLV p4_vis;		// momenta of visible particles
	unsigned char decayMode;
	//  0 - undefined
	//	1 - electron
	//	2 - muon
	// >2 - hadronic
	//      3 - 1prong
	//      4 - 3prong
	//      5 - >3prong
	// most significant bit (1<<7):
	//		0 = tau
	//		1 = descendant of a tau
	RMPoint vertex;

	static const int DescendantPosition = 7;
	static const int DescendantMask = 1 << DescendantPosition;

	bool isElectronicDecay() const { return (decayMode & ~DescendantMask) == 1; }
	bool isMuonicDecay() const { return (decayMode & ~DescendantMask) == 2; }
	bool isHadronicDecay() const { return (decayMode & ~DescendantMask) > 2; }

	bool isDescendant() const { return (decayMode & DescendantMask) != 0; }
};
typedef std::vector<KDataGenTau> KDataGenTaus;

#endif
