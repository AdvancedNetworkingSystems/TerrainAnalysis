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


process_links <- function(du, bw){
  df_srtm = data.frame(
    Loss=du$loss_srtm
  )
  
  df_ds = data.frame(
    Loss = du$loss_downscale
  )
  
  df = data.frame(
    Loss = du$loss
  )
  
  gp_h = ggplot(data = df_srtm, aes(Loss))+
    geom_histogram(aes(y= ..density.., fill="Lidar Downsampled"), binwidth = bw, data=df_ds, alpha=0.5) +
    geom_histogram(aes(y= ..density.., fill="Lidar"), binwidth = bw, data=df, alpha=0.5)+
    geom_histogram(aes(y= ..density.., fill="SRTM"), binwidth = bw, alpha=0.5) +
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

du8 <- read.csv('/home/gabriel/WORKS/Megasimulatore/TerrainAnalysis/data/lyon_8_links.csv')
process_links(du8, 5)
ggsave(filename = "/home/gabriel/WORKS/Megasimulatore/TerrainAnalysis/graph/lyon_bins_8.pdf")


du43 <- read.csv('/home/gabriel/WORKS/Megasimulatore/TerrainAnalysis/data/lyon_43_links.csv_0')
process_links(du43, 5)
ggsave(filename = "/home/gabriel/WORKS/Megasimulatore/TerrainAnalysis/graph/lyon_bins_43.pdf")
df43 = data.frame(
  Loss = du43[du43$status!=0,]$loss
)

ggplot(df43, aes(Loss))+
  geom_histogram(aes(y=..density..), binwidth = 5)


du86 <- read.csv('/home/gabriel/WORKS/Megasimulatore/TerrainAnalysis/data/lyon_86_links.csv')
process_links(du86, 5)
ggsave(filename = "/home/gabriel/WORKS/Megasimulatore/TerrainAnalysis/graph/lyon_bins_86.pdf")
df86 = data.frame(
  Loss = du86[du86$status!=0,]$loss
)
ggplot(df86, aes(Loss))+
  geom_histogram(aes(y=..density..), binwidth = 5)+
  



du173 <- read.csv('/home/gabriel/WORKS/Megasimulatore/TerrainAnalysis/data/lyon_173_links.csv_0')
process_links(du173, 5)
ggsave(filename = "/home/gabriel/WORKS/Megasimulatore/TerrainAnalysis/graph/lyon_bins_173.pdf")
df173 = data.frame(
  Loss = du173[du143$status!=0,]$loss
)
ggplot(df173, aes(Loss))+
  geom_histogram(aes(y=..density..), binwidth = 5)


du867 <- read.csv('/home/gabriel/WORKS/Megasimulatore/TerrainAnalysis/data/lyon_links_srtm_lidar_1x1.csv')
df = data.frame(
  Loss = du867[du867$status!=0,]$loss
)
ggplot(df, aes(Loss))+
  geom_histogram(aes(y=..density..), binwidth = 5)

ks.test(x=du867$loss, y=du8$loss)
ks.test(x=du867$loss, y=du43$loss)
ks.test(x=du867$loss, y=du86$loss)


ggplot(data.frame(Status=du8[du8$status!=0,]$status),  aes(Status))+
  geom_histogram(aes(y=..density.., fill="100%"),data = data.frame(Status=du867[du867$status!=0,]$status), binwidth = 1, alpha=0.5) +
  geom_histogram(aes(y=..density.., fill="20%"),data = data.frame(Status=du173[du173$status!=0,]$status), binwidth = 1, alpha=0.5) +
  geom_histogram(aes(y=..density.., fill="10%"),data = data.frame(Status=du86[du86$status!=0,]$status), binwidth = 1, alpha=0.5)
  #geom_histogram(aes(y=..density.., fill="5%"),data = data.frame(Status=du43[du43$status!=0,]$status), binwidth = 1, alpha=0.5)+ 
  #geom_histogram(aes(y=..density.., fill="1%"), binwidth = 1, alpha=0.5)




plot(ecdf(du86[du86$status!=0,]$loss))

fks.test(x=du867[du867$status!=0,]$status, y=du8[du8$status!=0,]$status)
ks.test(x=du867[du867$status!=0,]$status, y=du43[du43$status!=0,]$status)
ks.test(x=du867[du867$status!=0,]$status, y=du86[du86$status!=0,]$status)
ks.test(x=du867[du867$status!=0,]$loss, y=du173[du173$status!=0,]$loss)
ks.test(x=du867[du867$status!=0,]$loss, y=du867[du867$status!=0,]$loss)

ks.test()
plot(density(du867[du867$status!=0,]$loss))
lines(density(du173[du173$status!=0,]$loss), col="red")
lines(density(du86[du86$status!=0,]$loss), col="blue")
lines(density(du43[du43$status!=0,]$loss), col="green")
lines(density(du8[du8$status!=0,]$loss), col="yellow")

plot()

plot(density(du867[du867$status!=0,]$status))
lines(density(du173[du173$status!=0,]$status), col="red")
lines(density(du86[du86$status!=0,]$status), col="blue")
lines(density(du43[du43$status!=0,]$status), col="green")
lines(density(du8[du8$status!=0,]$status), col="yellow")






n = length(du867[du867$status!=0,]$loss)
m = length(du86[du86$status!=0,]$loss)
m = length(du43[du43$status!=0,]$loss)
m = length(du8[du8$status!=0,]$loss)

summary(du867[du867$status!=0,]$loss)
summary(du86[du86$status!=0,]$loss)
summary(du43[du43$status!=0,]$loss)

1.36*sqrt((n+m)/n*m)

qqplot(x=du867[du867$status!=0,]$loss, y=du43[du43$status!=0,]$loss)

process_links(du867, 5)
ggsave(filename = "/home/gabriel/WORKS/Megasimulatore/TerrainAnalysis/graph/lyon_bins_867.pdf")


process_heigth(dt)



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
