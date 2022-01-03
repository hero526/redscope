# set terminal pngcairo  transparent enhanced font "arial,10" fontscale 1.0 size 600, 400 
# set output 'boxplot.1.png'
set title "Distribution of cycles of the multi-request-processing, grouped by number of multi-request,\n assign individual colors (linetypes) to number of expriment clients\n" 
set xlabel "MULTI-REQUESTS"
set ylabel "CYCLES"

set border 5 front lt black linewidth 1.000 dashtype solid
# set boxwidth 0.2 absolute
# set style fill solid 0.50 border lt -1
set key outside right
set style increment default
set pointsize 0.5
set style data boxplot
set xtics border in scale 0,0 nomirror norotate autojustify
set xtics  norangelimit 
# set xtics   ("1" 1, "2" 1.00000, "C" 2.00000, "D" 3.0000)
# set xtics ("1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16")
# set xtics ("1" "2" "3" "4" "5" "6" "7" "8" "9" "10" "11" "12" "13" "14" "15" "16")
set xtics ("MRQ1" 1, "MRQ2" 2)
set xtics()
set ytics border in scale 1,0.5 nomirror norotate  autojustify
set xrange [ * : * ] noreverse writeback
set x2range [ * : * ] noreverse writeback
set yrange [ 0.00000 : * ] noreverse nowriteback
set y2range [ * : * ] noreverse writeback
set zrange [ * : * ] noreverse writeback
set cbrange [ * : * ] noreverse writeback
set rrange [ * : * ] noreverse writeback

# set style boxplot label off
set style boxplot sorted
set style fill empty
# set print "-"

# plot for [i=ARG2:ARG3] \
# 'multi-'.ARG1.'-client'.i.'.dat' using (0.0+i*0.1):2:(0.01):1 title 'cli'.i

# plot \
# 'multi-redis_insert-client1.dat' using (1-0.3):2:(0.01):1 title 'cli1', \
# 'multi-redis_insert-client2.dat' using (1-0.2):2:(0.01):1 title 'cli2', \
# 'multi-redis_insert-client3.dat' using (1-0.1):2:(0.01):1 title 'cli3', \
# 'multi-redis_insert-client4.dat' using (1):2:(0.01):1 title 'cli4', \
# 'multi-redis_insert-client8.dat' using (1+0.1):2:(0.01):1 title 'cli8', \
# # 'multi-redis_insert-client16.dat' using (1+0.2):2:(0.01):1 title 'cli16'

# plot \
# 'reuse_conn/multi-redis_insert-client1.dat' using (1):2:(0.01):1 title 'cli1', \
# 'reuse_conn/multi-redis_insert-client2.dat' using (1):2:(0.01):1 title 'cli1', \
# 'reuse_conn/multi-redis_insert-client3.dat' using (1):2:(0.01):1 title 'cli1', \
# 'reuse_conn/multi-redis_insert-client4.dat' using (1):2:(0.01):1 title 'cli2', \
# 'reuse_conn/multi-redis_insert-client8.dat' using (1):2:(0.01):1 title 'cli2', \
# 'reuse_conn/multi-redis_insert-client16.dat' using (1):2:(0.01):1 title 'cli2'

plot \
for [i=1:2]'reuse_conn/multi-redis_insert-client1.dat' using (i):2:(0.01):1 title 'cli1', \

# plot 'multi-redis_insert-client1.dat' 

pause -1 'Hit <cr> to continue: Compare sub-datasets'