#ifndef KAPPA_HITPRODUCER_H
#define KAPPA_HITPRODUCER_H

#include "KBaseMultiLVProducer.h"
#include <SimDataFormats/TrackingHit/interface/PSimHit.h>

struct KHitProducer_Product
{
	typedef std::vector<KDataHit> type;
	static const std::string id() { return "std::vector<KDataHit>"; };
	static const std::string producer() { return "KHitProducer"; };
};

class KHitProducer :
	public KRegexMultiProducer<edm::View<PSimHit>, KHitProducer_Product>,
	public KCommonVectorProducer<edm::View<PSimHit>, KHitProducer_Product>
{
public:
	KHitProducer(const edm::ParameterSet &cfg, TTree *_event_tree, TTree *_run_tree) :
		KRegexMultiProducer<edm::View<PSimHit>, KHitProducer_Product>(cfg, _event_tree, _run_tree),
		KCommonVectorProducer<edm::View<PSimHit>, KHitProducer_Product>(cfg) {}
	virtual ~KHitProducer() {};
protected:
	virtual void clearProduct(KManualMultiProducer<edm::View<PSimHit>, KHitProducer_Product>::OutputType &out) { out.clear(); }

	virtual void fillProduct(
		const KManualMultiProducer<edm::View<PSimHit>, KHitProducer_Product>::InputType &in,
		KManualMultiProducer<edm::View<PSimHit>, KHitProducer_Product>::OutputType &out,
		const std::string &name, const edm::InputTag *tag, const edm::ParameterSet &pset)
	{
		KCommonVectorProducer<edm::View<PSimHit>, KHitProducer_Product>::fillProduct(in, out, name);
	}

	virtual void fillSingle(const SingleInputType &in, SingleOutputType &out)
	{
		out.theta = in.thetaAtEntry();
		out.phi = in.phiAtEntry();
		out.pAbs = in.pabs();
		out.energyLoss = in.energyLoss();
	}
};

#endif