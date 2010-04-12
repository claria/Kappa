#ifndef KAPPA_TRACK_H
#define KAPPA_TRACK_H

#include "KBasic.h"

enum KTrackQuality
{
	TQ_Loose = 0, TQ_Tight = 1, TQ_HighPurity = 2, TQ_Confirmed = 3, TQ_GoodIterative = 4
};

struct KDataTrack : public KDataLV
{
	RMPoint ref;	// reference point ("vertex")
	char charge;
	float chi2, nDOF;
	float errPt, errEta, errPhi, errDxy, errDz;
	int nPixelHits,nStripHits; //dp
	int quality;

	double getDxy(KDataVertex * pv)
	{
		if (!pv)
			return -1.;
		return (
				- (ref.x()-pv->position.x()) * p4.y()
				+ (ref.y()-pv->position.y()) * p4.x()
			) / sqrt(p4.Perp2());
	}

	/*
		mode:
			0 - dxy
			1 - dxy/error(track)
			2 - dxy/sqrt(error(track)**2 + error(vertex)**2)
	*/
	double getIP(KDataVertex * pv, unsigned int mode = 0)
	{
		if (!pv)
			return -10000.;

		switch(mode)
		{
			case 0:
				return getDxy(pv);
				break;
			case 1:
				return getDxy(pv) / errDxy;
				break;
			case 2:
				ROOT::Math::SVector<double,3> orthog;
				orthog[0] = p4.y();
				orthog[1] = -p4.x();
				orthog[2] = 0;

				float vtxErr2 = ROOT::Math::Similarity(pv->covariance, orthog) / p4.Perp2();
				return getDxy(pv) / sqrt(errDxy*errDxy + vtxErr2 );
				break;
		}
		return -10000.;
	}
};
typedef std::vector<KDataTrack> KDataTracks;

#endif
