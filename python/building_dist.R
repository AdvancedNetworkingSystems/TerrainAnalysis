process_heigth <- function(dt){
  data = dt[dt$height<210,]$height
    df3 = data.frame(
    Height= data
  )
  
  gp_h = ggplot(df3, aes(Height))+
    geom_histogram(aes(y=..density..), bins = 30) +
    #stat_function(fun = dlogis, args = list(location = estimate_l[1], scale = estimate_l[2]), col="red") +
    theme_bw()+ 
    labs(y = "Density")
  
  #plot(gp_h)
  
  descdist(data)
  #plot(fitdist(data, "norm"))
  print(summary(data))
  
}


process_links <- function(du){
  df_srtm = data.frame(
    Loss=du[(du$status_srtm==3 | du$status_srtm ==1 | du$status_srtm == 0) & du$loss_srtm != 0 ,]$loss_srtm
  )
  
  df_ds = data.frame(
    Loss = du[(du$status_downscale==3 | du$status_downscale ==1 | du$status_downscale == 0) & du$loss_downscale != 0 ,]$loss_downscale
  )
  
  df = data.frame(
    Loss = du[(du$status==3 | du$status==1 | du$status== 0) & du$loss!= 0 ,]$loss
  )
  
  gp_h = ggplot(data = df_srtm, aes(Loss))+
    geom_density(aes(colour="SRTM")) +
    geom_density(aes(colour="Lidar Downsampled"), data=df_ds) +
    geom_density(aes(colour="Lidar"), data=df)+
    scale_colour_manual("", 
                        breaks = c("SRTM", "Lidar Downsampled", "Lidar"),
                        values = c("red", "green", "blue")) +
    theme_bw()+
    labs(y = "Density")
  
  plot(gp_h)
  #descdist(links)
  #plot(fitdist(links, "gamma"))
}


require("xtable")
require("ggplot2")
require("fitdistrplus")
require("anytime")
require("corrplot")
library(reshape2)
dt <- read.csv('/home/gabriel/WORKS/Megasimulatore/TerrainAnalysis/data/lyon_height.csv')
du <- read.csv('/home/gabriel/WORKS/Megasimulatore/TerrainAnalysis/data/lyon_links_srtm_lidar_1x1.csv')

process_heigth(dt)


process_links(du)

errors = length(du[du$status_lidar==-1 | du$status_srtm ==-2,]$link)
status = c('1'=0,'2'=1,'3'=3)

mat = matrix(nrow=3, ncol=3)
labels =  c("No LOS", "Los Free", "Fresnel Free")
rownames(mat) <-  labels
colnames(mat) <-  labels


len = length(du$link)
tot = 0
#LIDAR vs DS
for(i in seq(1,3)){
  for(j in seq(1,3)){
    n_changed = length(du[du$status==status[[i]] & du$status_downscale==status[[j]],]$b1)
    mat[i,j] = n_changed
    tot = tot +  n_changed
    print(paste("from status ",labels[[i]]," to status ",labels[[j]],n_changed))
  }
}

#DS vs SRTM
tot=0
mat1 = matrix(nrow=3, ncol=3)
rownames(mat1) <-  labels
colnames(mat1) <-  labels
for(i in seq(1,3)){
  for(j in seq(1,3)){
    n_changed = length(du[du$status_downscale==status[[i]] & du$status_srtm==status[[j]],]$b1)
    mat1[i,j] = n_changed
    tot = tot +  n_changed
    print(paste("from status ",labels[[i]]," to status ",labels[[j]],n_changed))
  }
}




du[du$status==2,]$status  
