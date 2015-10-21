sudo yum install git-core boost-devel gcc-c++

cd ..
wget http://geos.refractions.net/downloads/geos-3.0.0.tar.bz2
tar -jxvf geos-3.0.0.tar.bz2
cd geos-3.0.0
./configure
sudo make install
