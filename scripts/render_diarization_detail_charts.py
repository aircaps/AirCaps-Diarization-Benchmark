"""Export supplementary benchmark charts from the canonical result manifest."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Patch
ROOT=Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'results/website.json').read_text());models=sorted(d['models'],key=lambda m:m['macro7'])
font=FontProperties(fname=ROOT/'figures/resources/plex.ttf');serif=FontProperties(fname=ROOT/'figures/resources/newsreader.ttf')
bg='#f3f0e7';ink='#1b1b18';muted='#69685f';purple='#4c3a91'
colors=['#4c3a91','#70998e','#c89760','#7794b0','#a7b89b','#b8868f','#9182b2','#bca985','#71808b','#648ca5','#a4a2a0']
color={m['name']:c for m,c in zip(models,colors)}
def val(m,c):return m['values'][d['corpora'].index(c)]
def style(ax):
 ax.set_facecolor(bg);ax.set_axisbelow(True)
 for sp in ax.spines.values():sp.set_visible(False)
 ax.tick_params(length=0,pad=8,labelcolor=muted)
 for t in ax.get_xticklabels()+ax.get_yticklabels():t.set_fontproperties(font);t.set_fontsize(11)
from PIL import Image, ImageOps
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
logos=['aircaps','but','pyannote','nvidia','pyannote','alibaba','pyannote','elevenlabs','assemblyai','meta','xai']
logo_map={m['name']:logo for m,logo in zip(models,logos)}
short=['AirCaps\nDiarization-v1','DiariZen\nLarge v2','Precision-3','Nemotron 3\nDiarization','Community-1','3D-Speaker','pyannote 3.1','Scribe v2','Universal 3.5\nPro','Muse Voice\nTranscribe','Grok Voice\nTranscribe 2.0']
def logo(ax,m,xy,coords,size):
 key=logo_map[m['name']];path=ROOT/'figures/resources/aircaps-icon.png' if key=='aircaps' else ROOT/('figures/resources/'+key+'.png')
 im=ImageOps.contain(Image.open(path).convert('RGBA'),(80,80),Image.Resampling.LANCZOS)
 ax.add_artist(AnnotationBbox(OffsetImage(im,zoom=size),xy,xycoords=coords,frameon=False,annotation_clip=False))
fig=plt.figure(figsize=(20,10),facecolor=bg);ax=fig.add_axes([.055,.23,.925,.57]);cs=['notsofar','alimeeting','callhome','aishell4'];palette=['#4c3a91','#70998e','#c89760','#7794b0'];x=np.arange(len(models));width=.19
for j,c in enumerate(cs):
 positions=x+(j-1.5)*width
 ax.bar(positions,[val(m,c) for m in models],width=width*.91,color=palette[j],zorder=3)
 for pos,m in zip(positions,models):
  ax.text(pos,val(m,c)+.65,f'{val(m,c):.1f}%',ha='center',va='bottom',rotation=0,fontproperties=font,fontsize=7,color=ink,zorder=4)

for i,m in enumerate(models):
 logo(ax,m,(i,-.085),('data','axes fraction'),.38)
 ax.text(i,-.17,short[i],transform=ax.get_xaxis_transform(),ha='center',va='top',fontproperties=font,fontsize=12,color=purple if i==0 else ink,clip_on=False)
ax.set_xlim(-.6,10.6);ax.set_ylim(0,63);ax.set_xticks([]);ax.set_yticks(range(0,61,10));ax.set_yticklabels([f'{i}%' for i in range(0,61,10)]);style(ax);ax.yaxis.grid(color='#dedacf',linewidth=.8)
fig.text(.055,.94,'Diarization by dataset',fontproperties=serif,fontsize=32,color=ink)
fig.legend(handles=[Patch(color=c,label=n) for c,n in zip(palette,['NOTSOFAR-1','AliMeeting','CALLHOME','AISHELL-4'])],loc='upper left',bbox_to_anchor=(.05,.895),ncol=4,frameon=False,prop=FontProperties(fname=font.get_file(),size=13),columnspacing=3)
fig.savefig(ROOT/'figures/diarization-dataset-breakdown.png',dpi=240,facecolor=bg);plt.close(fig)
lookup={m['name']:m for m in models};selected=[lookup[n] for n in ['AirCaps Diarization-v1','ElevenLabs Scribe v2','AssemblyAI U3.5 Pro','Meta Muse Voice Transcribe','Grok Voice Transcribe 2.0']]
fig=plt.figure(figsize=(20,12),facecolor=bg);ax=fig.add_axes([.145,.085,.72,.73]);cs=d['primary_corpora'];labels={'aishell4':'AISHELL-4','alimeeting':'AliMeeting','ami':'AMI-SDM','notsofar':'NOTSOFAR-1','ramc':'RAMC','dihard3':'DIHARD III','callhome':'CALLHOME'}
for i,c in enumerate(cs):
 for j,m in enumerate(selected):
  y=i+(j-2)*.17;v=val(m,c);ax.barh(y,v,height=.14,color=color[m['name']],zorder=3);ax.text(v+.35,y,f'{v:.2f}',va='center',fontproperties=font,fontsize=11,color=purple if j==0 else muted);logo(ax,m,(-.017,y),('axes fraction','data'),.13)
 best=min(val(m,c) for m in selected[1:]);change=(val(selected[0],c)/best-1)*100
 ax.text(1.14,i,f'{change:+.1f}%'.replace('-','−'),transform=ax.get_yaxis_transform(),ha='right',va='center',fontproperties=font,fontsize=17,color=purple if change<0 else '#986746',clip_on=False)
ax.set_ylim(6.6,-.65);ax.set_xlim(0,59);ax.set_xticks(range(0,60,10));ax.set_xticklabels([f'{i}%' for i in range(0,60,10)]);ax.set_yticks(range(7));ax.set_yticklabels([labels[c] for c in cs]);style(ax);ax.tick_params(axis='y',pad=36);ax.xaxis.grid(color='#dedacf',linewidth=.8)
fig.text(.055,.95,'Against leading cloud ASR models',fontproperties=serif,fontsize=32,color=ink)
fig.legend(handles=[Patch(color=color[m['name']],label=m['name']) for m in selected],loc='upper left',bbox_to_anchor=(.05,.91),ncol=5,frameon=False,prop=FontProperties(fname=font.get_file(),size=12),columnspacing=1.5)
fig.text(.968,.83,'AirCaps vs best competitor',ha='right',fontproperties=font,fontsize=11,color=muted)
fig.text(.145,.035,'DER (%)',fontproperties=font,fontsize=11,color=muted)
fig.text(.968,.035,'− lower DER / + higher DER',ha='right',fontproperties=font,fontsize=11,color=muted)
fig.savefig(ROOT/'figures/diarization-leading-models.png',dpi=240,facecolor=bg);plt.close(fig)
