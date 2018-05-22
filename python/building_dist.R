require("xtable")
require("ggplot2")
require("fitdistrplus")
require("anytime")
dt <- read.csv('/home/gabriel/WORKS/Megasimulatore/python/heigts.csv', sep = ",")

data = dt[dt$height<80,]$height

df3 = data.frame(
  Data=dt[dt$height<100,]$height
)

gp_h = ggplot(df3, aes(Data))+
  geom_histogram(aes(y=..density..), bins = 30) +
  #stat_function(fun = dlogis, args = list(location = estimate_l[1], scale = estimate_l[2]), col="red") +
  theme_bw()+ 
  labs(y = "Density")

plot(gp_h)

descdist(data)


plot(fitdist(data, "norm"))
