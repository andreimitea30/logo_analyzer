# LOGO SIMILARITY

The program was designed to extract websites from a dataframe in order to create groups 
of logos from different companies keeping track of colors, feelings and other characteristics.

## COMMAND LINE ARGUMENTS AND USAGE

The program is designed to be run with command line arguments depending on the action that the user wants to perform.

In order to run the program, you can use the following arguments:

 - `download`: This argument is used to download the logos from the web. The logos are downloaded in the `logos` folder.
In order to proceed to the following commands, it is mandatory to execute logo downloading first. More details about the
command can be found in the `DATAFRAME PARSING AND DUPLICATE REMOVAL` section.

 - `analyze`: This argument is used to analyze the logos. The analysis consists of three parts: color analysis, minimalism
and behavioral analysis. This command requires a second argument, consisting of the type of analysis the user wants to 
perform. The options are: `--type [color/minimalism/emotion]`.The results are stored in csv files with easy-to-understand names. More details about the command can be found 
in the `LOGO ANALYSIS` section.

 - `palette`: This argument is used to create a palette for each logo. The palettes are stored in the `palettes` folder.
More about the command can be found in the `PALETTE CREATION` section.

## DATAFRAME PARSING AND DUPLICATE REMOVAL

Firstly, I observed that the database has exact duplicates, which I removed, reducing the number 
of rows from about 4500 to roughly 3400. 

Next, it was obvious that some companies were registered in the dataframe with multiple 
sites from different regions. Analyzing the way the websites were named, I could see that
most of the brand names could be extracted with a simple split before `-` or `.`. These 
observations drastically reduced the number of entries in the dataframe from those 3400 to
approximately 1500.

Due to the fact that some sites were still duplicates, I decided it is easier to download 
the duplicated logos and then try to remove the duplicates using an image hash. This
results in a more accurate logo downloading process.

Because the downloading process was slow, I decided to download the logos in parallel. I used a maximum 
of 10 threads to do the downloading.

Afterward, I used an image histogram in order to determine the similarity grade between different logos. 
Due to some checks I did empirically, I decided that a similarity grade of 49% and is enough to consider
two logos as being the same, while also checking that the first 3 letters from the logo name are the same.

The result is a folder that contains all the logos from the companies in the dataframe, 
but does not contain the duplicates that would have slowed the process of interpreting the
given structure. Finally, from over 4500 rows to only *361 logos*.

## LOGO ANALYSIS

In order to provide different ways of viewing the logos, and also be able to create clusters of logos that
share some characteristics. I decided to use the following methods:

 - **Color Analysis**: 

This method consists of two parts. Both of them provide information about the main color of
the logo. The first part, that is included in the `analysis_color.csv` file, provides a table with the following
columns: `logo_name`, `main_color` (in RGB format), `main_color_name` (the name of the color in English). For this, I
used the `webcolors` library. The second part, that is included in the `color_analysis.md` file, provides a list of
logo groups that share the same main color. How I created the groups is that I chose a list of predefined colors, and
then I checked which logos have the main color that is closest to one of the predefined colors. The list of predefined
colors can be changed in order to provide clusters based on other colors categories.

 - **Minimalism Analysis**:

This method provides a csv file name `analysis_minimalism.csv` that contains the following columns: `logo_name`, 
`minimalism?`. Basically, it tries to determine if the logo is minimalist or not. For this, I used the KMeans algorithm
in order to extract the 5 most important colors from the logo. Because the colors that were returned by this algorithm 
could've been shades of the same base color, I made use of the predefined colors introduced for the color analysis and 
reduced them to basic colors. By doing so, I bypassed both the different shades and gradients created by lighting, but 
also the different artifacts that could be produced by image analysis. Then, I checked if the logo has 2 or fewer colors. 
If it has 2 or fewer colors, then I considered it minimalist.

 - **Behavioral Analysis**:

The color of things can influence the way we perceive them. For example, certain companies could look for logos that 
inspire trust, while others could look for logos that inspire creativity. In order to provide a way to group logos based
on the feelings they inspire, I researched the way colors create feelings. I found out that the warmth of an image can be
a determinant factor in the way we perceive it. Taking this into account, I created a csv file named `analysis_emotion.csv`
that contains the following columns: `logo_name`, `emotion`. The warmth is basically a score that describes the overall
warmth of the logo. The score is calculated by summing the 8 most important colors from the logo and then assigning a score
to each color based on the warmth it provides. The score is between -1 and 1, where -1 is cold and 1 is warm. The warmth 
score then is converted into an emotion, based on some articles I read that indicate that the colder the logo, the more
serious it is perceived, while the warmer the logo, the more friendly it is perceived.

## PALETTE CREATION

In addition to the previous analysis, I decided to create a palette for each logo. The palette is created by extracting
the main colors from the logo, using the same KMeans algorithm, and creating a visual identity that each company can rely 
on in order to create ads or create a design blueprint for future brand related materials.

The extracted colors are sorted to ensure a visually appealing arrangement. The step function is used to sort the colors 
based on their luminance and hue. A new image is created to represent the color palette. The palette image is divided into 
blocks, each representing one of the main colors. The generated palette image can be found in the `palettes` folder with 
the same name as the original logo image.

## FUTURE IMPROVEMENTS

The code can be improved in various ways in order to provide a faster execution, and also to provide more accurate results.
The program is designed so that it can be easily parallelized, making it feasible to run on more complex datasets. The
analysis can be improved by using more advanced algorithms, such as neural networks, in order to provide a more accurate
result. Creating a neural network could result in also creating more advanced analysis, such as logo recognition, or even
creating a logo generator. Also, the implementation of some custom algorithms could also reduce the need of various imports
and, perhaps, improve the speed of the program.
