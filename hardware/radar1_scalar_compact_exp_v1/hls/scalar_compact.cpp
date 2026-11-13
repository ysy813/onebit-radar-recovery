#include <ap_int.h>
#include "parameters.h"
typedef ap_uint<64> word;
typedef ap_uint<13> feature;
typedef ap_int<32> act;
typedef ap_int<48> accum;
const int N=1024*512;
// 16 MiB scratch: canonical z, packed base4, score/final gain, gated support.
// Power remains unmodified until every gain has been calculated.
static ap_uint<40> root80(ap_uint<80> x){
    ap_uint<82> rem=0;ap_uint<40> root=0;
    for(int i=39;i>=0;--i){rem=(rem<<2)|ap_uint<82>((x>>(2*i))&3);ap_uint<82> trial=(ap_uint<82>(root)<<2)|1;root=root<<1;if(rem>=trial){rem-=trial;root|=ap_uint<40>(1);}}
    return root;
}
static act rounded(accum a){return act((a+32768)>>16);}
static act fifth(act x){
#pragma HLS INLINE
    act v=x;
    for(int i=0;i<4;i++){
#pragma HLS UNROLL
        v=rounded(accum(v)*x);
    }return v;
}
static act clip(act x){return x>65536?act(65536):x< -65536?act(-65536):x;}
static unsigned predict(act x[40]){
#pragma HLS INLINE off
#pragma HLS ARRAY_PARTITION variable=x complete
    act a[32],b[16];
#pragma HLS ARRAY_PARTITION variable=a complete
#pragma HLS ARRAY_PARTITION variable=b complete
#pragma HLS ARRAY_PARTITION variable=W0 complete dim=2
#pragma HLS ARRAY_PARTITION variable=W1 complete dim=2
#pragma HLS ARRAY_PARTITION variable=W2 complete
L0: for(int o=0;o<32;o++){
#pragma HLS PIPELINE II=1
        accum s=B0[o];
        for(int i=0;i<40;i++){
#pragma HLS UNROLL
            s+=accum(x[i])*ap_int<20>(W0[o][i]);
        }act v=rounded(s);a[o]=v>0?v:act(0);
    }
L1: for(int o=0;o<16;o++){
#pragma HLS PIPELINE II=1
        accum s=B1[o];
        for(int i=0;i<32;i++){
#pragma HLS UNROLL
            s+=accum(a[i])*ap_int<20>(W1[o][i]);
        }act v=rounded(s);b[o]=v>0?v:act(0);
    }
    accum s=B2;
    for(int i=0;i<16;i++){
#pragma HLS UNROLL
        s+=accum(b[i])*ap_int<20>(W2[i]);
    }
    int index=((rounded(s)+32)>>6).to_int()+16384;
    if(index<0)index=0;if(index>32768)index=32768;
    return GAIN[index];
}
static feature get_support(ap_uint<52> table[N/4],int r,int a){
#pragma HLS INLINE
    unsigned p=((r&1023)<<9)|(a&511);return (table[p>>2]>>((p&3)*13))&8191;
}
static int even_round(int num,int den){
#pragma HLS INLINE
    int s=num<0?-1:1,n=num<0?-num:num,q=n/den,rem=n%den;
    if(2*rem>den||(2*rem==den&&(q&1)))q++;return s*q;
}
static unsigned protect(word p,word mx3,word mx9,word peak,act x[40],unsigned g){
#pragma HLS INLINE off
    long long a0=x[8].to_int64(),a3=x[9].to_int64(),a5=x[10].to_int64();
    long long d3=3*a0-a3,d5=5*a0-a5;if(d3<0)d3=-d3;if(d5<0)d5=-d5;
    bool explained=(a3>=16384&&2*d3<=a3)||(a5>=16384&&2*d5<=a5);
    word lower=peak/10000+word((peak%10000)!=0);
    bool near=p>=lower && p>=mx3/2+word(mx3[0]);
    bool weak=p>0&&p<=peak/16;
    unsigned conf=g>4096?(g>=8192?4096:g-4096):0;
    if(weak&&(p==mx9||near)&&!explained&&g<16384)g+=((16384-g)*conf+2048)>>12;
    conf=g>4096?(g>=8192?4096:g-4096):0;
    int center=x[0].to_int()>>4,mean=x[3].to_int()>>4;if(mean<128)mean=128;
    int n=5*center-7*mean;if(n<0)n=0;
    unsigned compact=(n*4096+mean/2)/mean;if(compact>4096)compact=4096;
    if(p>=lower&&p<=peak/16&&p==mx9&&!explained&&g<16384){
        unsigned weight=(compact*conf+2048)>>12;g+=((16384-g)*weight+2048)>>12;
    }
    if(p==peak)g=16384;return g;
}
extern "C" void scalar_gain(word *power,word *work,unsigned &suppressed,unsigned long long &peak_power){
#pragma HLS INTERFACE m_axi port=power offset=direct bundle=mem depth=524288 max_read_burst_length=64 max_write_burst_length=64 num_read_outstanding=4
#pragma HLS INTERFACE m_axi port=work offset=direct bundle=mem depth=2097152 max_read_burst_length=64 max_write_burst_length=64 num_read_outstanding=4
#pragma HLS INTERFACE ap_none port=suppressed
#pragma HLS INTERFACE ap_none port=peak_power
#pragma HLS INTERFACE ap_ctrl_hs port=return
    static ap_uint<52> support[N/4];
#pragma HLS BIND_STORAGE variable=support type=ram_2p impl=uram
    static feature lines[9][512];
#pragma HLS ARRAY_PARTITION variable=lines complete dim=1
#pragma HLS BIND_STORAGE variable=lines type=ram_2p impl=bram
    static word raw[9][512];
#pragma HLS ARRAY_PARTITION variable=raw complete dim=1
#pragma HLS BIND_STORAGE variable=raw type=ram_2p impl=bram
    word peak=0;
PEAK: for(int i=0;i<N;i++){
#pragma HLS PIPELINE II=1
        word p=power[i];if(p>peak)peak=p;
    }
    peak_power=peak.to_uint64();suppressed=0;if(peak==0)return;
    ap_uint<40> divisor=root80(ap_uint<80>(peak)<<16);
NORMALIZE: for(int r=0;r<1024;r++)for(int a=0;a<512;a++){
        ap_uint<40> v=root80(ap_uint<80>(power[r*512+(a^256)])<<16);
        ap_uint<57> numerator=ap_uint<57>(v)*65535+divisor/2;
        unsigned m=(numerator/divisor).to_uint();if(m>65535)m=65535;work[r*512+a]=ROOT5[m];
    }
INIT: for(int j=0;j<9;j++)for(int a=0;a<512;a++){
#pragma HLS PIPELINE II=1
        lines[j][a]=work[((j-4)&1023)*512+a];
    }
STATS_R: for(int r=0;r<1024;r++){
        ap_uint<52> packed=0;
STATS_A: for(int a=0;a<512;a++){
            unsigned sum3=0,sum9=0,mx=0;
            for(int j=0;j<9;j++)for(int k=-4;k<=4;k++){
#pragma HLS PIPELINE II=1
                unsigned v=lines[(r+j)%9][(a+k)&511];sum9+=v;
                if(j>=3&&j<=5&&k>=-1&&k<=1){sum3+=v;if(v>mx)mx=v;}
            }
            work[N+r*512+a]=word(lines[(r+4)%9][a])|(word(mx)<<13)|(word((sum3+4)/9)<<26)|(word((sum9+40)/81)<<39);
            packed|=ap_uint<52>(mx)<<((a&3)*13);if((a&3)==3){support[(r*512+a)>>2]=packed;packed=0;}
        }
        if(r<1023)for(int a=0;a<512;a++){
#pragma HLS PIPELINE II=1
            lines[r%9][a]=work[((r+5)&1023)*512+a];
        }
    }
    unsigned sums[512];
#pragma HLS BIND_STORAGE variable=sums type=ram_2p impl=bram
    for(int a=0;a<512;a++)sums[a]=0;
    for(int j=-15;j<=15;j++)for(int a=0;a<512;a++){
#pragma HLS PIPELINE II=1
        sums[a]+=work[(j&1023)*512+a].to_uint();
    }
SCORE_R: for(int r=0;r<1024;r++)for(int a=0;a<512;a++){
        unsigned z=work[r*512+a].to_uint(),mean=(sums[a]+15)/31,den=mean<128?128:mean;
        int n=20*int(z)-24*int(den);if(n<0)n=0;
        unsigned ratio=(n*4096+(5*den)/2)/(5*den);if(ratio>4096)ratio=4096;
        work[2*N+r*512+a]=(z*ratio+2048)>>12;
        sums[a]=sums[a]-work[((r-15)&1023)*512+a].to_uint()+work[((r+16)&1023)*512+a].to_uint();
    }
    for(int j=0;j<3;j++)for(int a=0;a<512;a++)lines[j][a]=work[2*N+((j-1)&1023)*512+a];
GATE_R: for(int r=0;r<1024;r++){
        for(int a=0;a<512;a++){
            unsigned mx=0;
            for(int j=0;j<3;j++)for(int k=-1;k<=1;k++){
#pragma HLS PIPELINE II=1
                unsigned v=lines[(r+j)%3][(a+k)&511];if(v>mx)mx=v;
            }work[3*N+r*512+a]=mx;
        }
        if(r<1023)for(int a=0;a<512;a++)lines[r%3][a]=work[2*N+((r+2)&1023)*512+a];
    }
    for(int j=0;j<9;j++)for(int a=0;a<512;a++){
#pragma HLS PIPELINE II=1
        lines[j][a]=work[((j-4)&1023)*512+a];raw[j][a]=power[((j-4)&1023)*512+(a^256)];
    }
    unsigned changed=0;
INFER_R: for(int r=0;r<1024;r++){
INFER_A: for(int a=0;a<512;a++){
        act x[40];
#pragma HLS ARRAY_PARTITION variable=x complete
        word f=work[N+r*512+a];
        x[0]=act(f.range(12,0))<<4;x[1]=act(f.range(25,13))<<4;x[2]=act(f.range(38,26))<<4;x[3]=act(f.range(51,39))<<4;
        unsigned p3=0,p5=0;
        for(int kr=0;kr<3;kr++)for(int ka=0;ka<3;ka++){
#pragma HLS PIPELINE II=1
            unsigned v=get_support(support,even_round(-r+kr*1024,3),even_round(-a+ka*512,3));if(v>p3)p3=v;
        }
        for(int kr=0;kr<5;kr++)for(int ka=0;ka<5;ka++){
#pragma HLS PIPELINE II=1
            unsigned v=get_support(support,even_round(r+kr*1024,5),even_round(a+ka*512,5));if(v>p5)p5=v;
        }
        x[4]=act(p3)<<4;x[5]=act(p5)<<4;
        x[6]=act(work[3*N+((-3*r)&1023)*512+((-3*a)&511)])<<4;
        x[7]=act(work[3*N+((5*r)&1023)*512+((5*a)&511)])<<4;
        for(int i=0;i<5;i++)x[8+i]=fifth(x[i==0?0:i+3]);
        x[13]=clip(3*x[8]-x[9]);x[14]=clip(5*x[8]-x[10]);x[15]=x[8]-fifth(x[2]);
        int idx=16;
        for(int dr=-2;dr<=2;dr++)for(int da=-2;da<=2;da++)if(dr!=0||da!=0)x[idx++]=act(lines[(r+4+dr)%9][(a+da)&511])<<4;
        word mx3=0,mx9=0;
        for(int j=0;j<9;j++)for(int k=-4;k<=4;k++){
#pragma HLS PIPELINE II=1
            word v=raw[(r+j)%9][(a+k)&511];if(v>mx9)mx9=v;if(j>=3&&j<=5&&k>=-1&&k<=1&&v>mx3)mx3=v;
        }
        unsigned g=protect(raw[(r+4)%9][a],mx3,mx9,peak,x,predict(x));
        work[2*N+r*512+a]=g;if(g<16384)changed++;
    }
        if(r<1023)for(int a=0;a<512;a++){
#pragma HLS PIPELINE II=1
            lines[r%9][a]=work[((r+5)&1023)*512+a];raw[r%9][a]=power[((r+5)&1023)*512+(a^256)];
        }
    }
APPLY: for(int r=0;r<1024;r++)for(int a=0;a<512;a++){
        unsigned g=work[2*N+r*512+a].to_uint();int p=r*512+(a^256);
        ap_uint<96> scaled=ap_uint<96>(power[p])*g*g+(ap_uint<96>(1)<<27);
        ap_uint<68> result=scaled>>28;power[p]=result>ap_uint<68>(0xffffffffffffffffULL)?word(0xffffffffffffffffULL):word(result);
    }
    suppressed=changed;
}
