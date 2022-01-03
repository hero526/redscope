# set terminal pngcairo  transparent enhanced font "arial,10" fontscale 1.0 size 600, 400 
# set output 'boxplot.1.png'
set title "Distribution of cycles of the multi-request-processing, grouped by number of multi-request,\n assign individual colors (dot-types) to each expriment condition\n" 
set xlabel "MULTI-REQUESTS"
set ylabel "CYCLES"

set border 5 front lt black linewidth 1.000 dashtype solid
set key outside right

plot \
'reuse_conn/multi-redis_insert-client1.dat' w p ls 1 title 're-cli1', \
'reuse_conn/multi-redis_insert-client2.dat' w p ls 2 title 're-cli2', \
'reuse_conn/multi-redis_insert-client3.dat' w p ls 3 title 're-cli3', \
'reuse_conn/multi-redis_insert-client4.dat' w p ls 4 title 're-cli4', \
'reuse_conn/multi-redis_insert-client8.dat' w p ls 8 title 're-cli8', \
'reuse_conn/multi-redis_insert-client16.dat' w p ls 6 title 're-cli16', \
'new_conn/multi-redis_insert-client4.dat' w p ls 7 title 'nw-cli4', \
'new_conn/multi-redis_insert-client8.dat' w p ls 5 title 'nw-cli8', \
'new_conn/multi-redis_insert-client16.dat' w p ls 9 title 'nw-cli16', \
'new_conn/multi-redis_insert-client24.dat' w p ls 10 title 'nw-cli24'

# plot 'multi-redis_insert-client1.dat' 

pause -1 'Hit <cr> to continue: Compare sub-datasets'