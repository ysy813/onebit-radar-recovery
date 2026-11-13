#include <ap_int.h>
#include <fstream>
#include <iostream>
#include <vector>
#include <string>
#include <cstdint>
typedef ap_uint<64> word;
extern "C" void scalar_gain(word*,word*,unsigned&,unsigned long long&);
int main(int argc,char**argv){
    if(argc!=2)return 2;std::string root=argv[1],name;const int N=524288;
    std::ifstream cases(root+"/cases.txt");if(!cases)return 3;
    std::vector<word> power(N),work(4*N);std::vector<uint64_t> p(N),expected(N);
    while(std::getline(cases,name)){
        if(name.empty())continue;std::string dir=root+"/"+name;
        std::ifstream in(dir+"/test_power.bin",std::ios::binary),ref(dir+"/expected_power.bin",std::ios::binary);
        if(!in||!ref)return 4;in.read((char*)p.data(),N*8);ref.read((char*)expected.data(),N*8);
        for(int i=0;i<N;i++)power[i]=p[i];unsigned changed=0;unsigned long long peak=0;
        scalar_gain(power.data(),work.data(),changed,peak);unsigned errors=0;
        std::ofstream out(dir+"/csim_power.bin",std::ios::binary);
        for(int i=0;i<N;i++){uint64_t v=power[i].to_uint64();out.write((char*)&v,8);if(v!=expected[i]){if(errors<8)std::cerr<<name<<" "<<i<<":"<<v<<" != "<<expected[i]<<" gain="<<work[2*N+(i/512)*512+((i%512)^256)]<<"\n";errors++;}}
        std::cout<<"HLS_POWER_COMPARE case="<<name<<" mismatches="<<errors<<" suppressed="<<changed<<" peak="<<peak<<std::endl;
        if(errors)return 5;
    }
    for(int i=0;i<N;i++)power[i]=0;unsigned changed=99;unsigned long long peak=99;scalar_gain(power.data(),work.data(),changed,peak);
    if(changed||peak)return 6;for(int i=0;i<N;i++)if(power[i]!=0)return 7;
    std::cout<<"HLS_CSIM_PASS zero_frame=PASS full_frames=3"<<std::endl;return 0;
}
