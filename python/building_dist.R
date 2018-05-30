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
  
  plot(gp_h)
  
  #descdist(data)
  #plot(fitdist(data, "norm"))
  print(summary(data))
  
}


process_links <- function(du){
  links = du[du$status==3 | du$status ==1,]$loss
  df3 = data.frame(
    Loss=links
  )
  
  gp_h = ggplot(df3, aes(Loss))+
    geom_histogram(aes(y=..density..), bins = 70) +
    #stat_function(fun = dlogis, args = list(location = estimate_l[1], scale = estimate_l[2]), col="red") +
    theme_bw()+ 
    labs(y = "Density")
  
  plot(gp_h)
  descdist(links)
  plot(fitdist(links, "gamma"))
}


require("xtable")
require("ggplot2")
require("fitdistrplus")
require("anytime")
require("corrplot")
dt <- read.csv('/home/gabriel/WORKS/Megasimulatore/TerrainAnalysis/data/lyon_height.csv')
du <- read.csv('/home/gabriel/WORKS/Megasimulatore/TerrainAnalysis/data/lyon_all_links_1x1.csv')

process_heigth(dt)

process_links(du)

errors = length(du[du$status_lidar==-1 | du$status_srtm ==-2,]$link)
status = c('1'=-2, '2'=-1,'3'=0,'4'=1,'5'=3)

mat = matrix(nrow=5, ncol=5)
labels =  c("Key Error","Error", "No LOS", "Los Free", "Fresnel Free")
rownames(mat) <-  labels
colnames(mat) <-  labels
len = length(du$link)
tot = 0
for(i in seq(1,5)){
  for(j in seq(1,5)){
    n_changed = length(du[du$status_lidar_ds==status[[i]] & du$status_srtm==status[[j]],]$link)
    mat[i,j] = n_changed
    tot = tot +  n_changed
    print(paste("from status ",labels[[i]]," to status ",labels[[j]],n_changed))
  }
}

length(du[du$status==-1 & du$status_ds==-1,]$b1)



du[du$status==2,]$status  
