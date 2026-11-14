% fairmeta.cls: the Meta FAIR preprint class, as distributed in the arXiv source
% of "ANTE: Anticipate, Then Execute" (arXiv:2610.15368, CC BY 4.0). The file
% itself carries no license notice. Local changes:
%   - MIRIX logo (figures/mirix_logo.png) in the title box instead of the AWS logo;
%   - \DisableLigatures skipped under XeTeX, so XeTeX builds too.

\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{fairmeta}
\LoadClassWithOptions{article}

\RequirePackage[top=2.25cm, bottom=2.5cm, left=2.5cm, right=2.5cm, columnsep=0.65cm]{geometry}
\RequirePackage{microtype}
\RequirePackage{placeins}
\RequirePackage{hyphenat}
\RequirePackage{setspace}
\RequirePackage{parskip}
\RequirePackage[latin, english]{babel}
\RequirePackage{lipsum}
\RequirePackage{etoolbox}

\RequirePackage{iftex}
\ifXeTeX\else\DisableLigatures[f]{family=sf*}\fi

\RequirePackage{graphicx}
\RequirePackage{subcaption}

\RequirePackage{booktabs}
\RequirePackage{multirow}
\RequirePackage{bm}
\newcommand{\nm}[1]{#1}

\RequirePackage[most]{tcolorbox}
\RequirePackage{xcolor}
\definecolor{metablue}{HTML}{6289a9}
\definecolor{metafg}{HTML}{1C2B33}

\definecolor{metabg}{HTML}{f3f6f4}

\RequirePackage{amsthm}
\RequirePackage{titlesec}
\titleformat*{\paragraph}{\normalfont}
\titleformat*{\section}{\Large\sffamily\bfseries}
\titleformat*{\subsection}{\large\sffamily\bfseries}
\titleformat*{\subsubsection}{\normalsize\sffamily\bfseries}
\RequirePackage{hyperref}
\RequirePackage[noabbrev,nameinlink]{cleveref}
\hypersetup{
  colorlinks,
  linkcolor=metablue,
  citecolor=metablue,
  urlcolor=metablue
}

\RequirePackage[round,authoryear]{natbib}
\def\bibfont{\small}

\DeclareTextFontCommand{\textbf}{\bfseries\sffamily}

\RequirePackage{caption}
\DeclareCaptionLabelSeparator{custom}{}
\DeclareCaptionFormat{custom}{{\sffamily\textbf{#1 #2}} #3}
\captionsetup{singlelinecheck=false,format=custom,labelsep=custom,font=normalsize}
\captionsetup[sub]{singlelinecheck=true,format=custom,labelsep=custom,font=normalsize}

\renewcommand*\ttdefault{cmvtt}
\RequirePackage[T1]{fontenc}
\RequirePackage[scaled=0.88]{helvet}

\renewcommand\addtolist[5][]{
  \begingroup
    \if\relax#3\relax\def\sep{}\else\def\sep{#5}\fi
    \let\protect\@unexpandable@protect 
    \xdef#3{\expandafter{#3}\sep #4[#1]{#2}}\endgroup
}

\newcommand\authorlist{}
\newcommand\authorformat[2][]{{\sffamily \bfseries #2$^{#1}$}}
\renewcommand\author[2][]{\addtolist[#1]{#2}{\authorlist}{\authorformat}{, }}

\newcommand\affiliationlist{}
\newcommand\affiliationformat[2][]{{\normalsize $^{#1}$#2}}
\newcommand\affiliation[2][]{\addtolist[#1]{#2}{\affiliationlist}{\affiliationformat}{, }}

\newcommand\contributionlist{}
\newcommand\contributionformat[2][]{{\small $^{#1}$#2}}
\newcommand\contribution[2][]{\addtolist[#1]{#2}{\contributionlist}{\contributionformat}{, }}

\newcommand\metadatalist{}
\newcommand\metadataformat[2][]{{\small {\sffamily \bfseries #1:} #2}}
\newcommand\metadata[2][]{\addtolist[#1]{#2}{\metadatalist}{\metadataformat}{\par}}

\renewcommand{\abstract}[1]{\def\abstractlist{{\color{metafg} #1}}}
\newcommand{\email}[1]{\href{mailto:#1}{\texttt{#1}}}

\renewcommand\date[1]{\metadata[Date]{#1}}
\newcommand\correspondence[1]{\metadata[Correspondence]{#1}}
\newcommand\authoremails[1]{\metadata[Author E-mails]{#1}}

\renewcommand{\title}[1]{\newcommand{\titlelist}{{\sffamily\bfseries\fontsize{19}{22.8}\selectfont #1}}}

\newcommand{\beginappendix}{\appendix{\huge\sffamily Appendix\par}}

\newcommand{\mymaketitle}{\tcbset{enhanced,frame hidden}
  \tcbset{left=0.5cm}
  \tcbset{right=0.5cm}
  \tcbset{top=0.5cm}
  \tcbset{bottom=0.5cm}
  \tcbset{arc=10pt}
  \tcbset{colback=metabg}
  \tcbset{before skip=0pt}
  \tcbset{grow to left by=1.5pt}
  \tcbset{grow to right by=1.5pt}
  \tcbset{overlay={\node[
    anchor=south east,
    inner sep=0pt,
    at=(frame.south east),
    xshift=-0.5cm,
    yshift=0.5cm] {\includegraphics[width=2cm]{figures/mirix_logo.png}};}}
  \begin{tcolorbox}
    \setlength{\parindent}{0cm}
    \setlength{\parskip}{0.5cm}
    {
      \setlength{\parskip}{0cm}
      \raggedright
      \nohyphens
      {
        \setstretch{1.618}
        \titlelist\par
      }
      \vskip 0.2cm
      \authorlist\par
      \vskip 0.2cm
      \affiliationlist\par
      \contributionlist\par
    }
    \abstractlist\par
    \vskip 0.5cm
    {
      \setlength{\parskip}{0cm}
      \ifdefempty{\metadatalist}{\vspace*{0.65cm}}{\metadatalist\par}
    }
  \end{tcolorbox}
  \tcbset{reset}
  \FloatBarrier
}

\if@twocolumn
\renewcommand{\maketitle}{
\twocolumn[\mymaketitle
  \vskip 0.38cm
]
}\else
\renewcommand{\maketitle}{
  \mymaketitle
}\fi
