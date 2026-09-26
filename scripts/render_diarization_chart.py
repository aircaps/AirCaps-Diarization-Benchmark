"""Rebuild the header PNG from full-precision website results. Requires matplotlib, Pillow."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib.patches import FancyBboxPatch
from PIL import Image, ImageOps
ROOT=Path(__file__).resolve().parents[1];res=ROOT/'figures/resources'
font=FontProperties(fname=res/'plex.ttf');serif=FontProperties(fname=res/'newsreader.ttf')
cream='#f3f0e7';purple='#4c3a91';ink='#1b1b18';muted='#69685f'
models=sorted(json.loads((ROOT/'results/website.json').read_text())['models'],key=lambda m:m['macro7'])
labels=[('AirCaps','Diarization-v1','aircaps'),('BUT Speech@FIT','DiariZen\nLarge v2','but'),('pyannoteAI','Precision-3','pyannote'),('NVIDIA','Nemotron 3\nDiarization','nvidia'),('pyannote','Community-1','pyannote'),('Alibaba','3D-Speaker','alibaba'),('pyannote','3.1','pyannote'),('ElevenLabs','Scribe v2','elevenlabs'),('AssemblyAI','Universal 3.5\nPro','assemblyai'),('Meta','Muse Voice\nTranscribe','meta'),('xAI','Grok Voice\nTranscribe 2.0','xai')]
fig=plt.figure(figsize=(20,10),facecolor=cream);ax=fig.add_axes([.06,.29,.925,.59],facecolor=cream)
ax.set_xlim(-.65,10.65);ax.set_ylim(0,46);ax.set_yticks([0,10,20,30,40]);ax.set_yticklabels(['0%','10%','20%','30%','40%'],fontproperties=font,fontsize=12,color=muted);ax.tick_params(axis='both',length=0,pad=12);ax.set_xticks([])
for sp in ax.spines.values():sp.set_visible(False)
ax.set_axisbelow(True);ax.yaxis.grid(True,color='#dedacf',linewidth=.8);ax.axhline(0,color='#bdb7aa',linewidth=1)
ax.axvspan(-.5,.5,color=purple,alpha=.055,zorder=0)
for i,(m,(team,label,logo)) in enumerate(zip(models,labels)):
 v=m['macro7'];color=purple if i==0 else '#aaa4bb'
 ax.add_patch(FancyBboxPatch((i-.37,0),.74,v,boxstyle='round,pad=0,rounding_size=0.16',linewidth=0,facecolor=color,zorder=3))
 ax.text(i,v+1.1,f'{v:.2f}%',ha='center',va='bottom',fontproperties=font,fontsize=18 if i==0 else 15,color=purple if i==0 else ink,weight='bold')
 file=ROOT/'figures/resources/aircaps-icon.png' if logo=='aircaps' else res/(logo+'.png')
 im=Image.open(file).convert('RGBA');im=ImageOps.contain(im,(90,90),Image.Resampling.LANCZOS)
 ab=AnnotationBbox(OffsetImage(im,zoom=.42),(i,-.105),xycoords=('data','axes fraction'),frameon=True,bboxprops={'boxstyle':'circle,pad=0.5','fc':cream,'ec':'#dedacf','lw':.7},annotation_clip=False);ax.add_artist(ab)
 ax.text(i,-.205,team,transform=ax.get_xaxis_transform(),ha='center',va='top',fontproperties=font,fontsize=11,color=purple if i==0 else muted,clip_on=False)
 ax.text(i,-.253,label,transform=ax.get_xaxis_transform(),ha='center',va='top',fontproperties=font,fontsize=13,color=purple if i==0 else ink,linespacing=1.3,clip_on=False)
fig.text(.06,.93,'Average Diarization Error Rate (DER) Across 7 Public Datasets',fontproperties=serif,fontsize=32,color=ink)
fig.savefig(ROOT/'figures/diarization-seven-corpus.png',dpi=240,facecolor=cream)
plt.close(fig)
