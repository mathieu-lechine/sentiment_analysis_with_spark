# Ceci est un bout de code qu'il faut coller a la fin du script
# qui entraine le modele.
# Cela va creer un fichier texte 'sauvegarde_MYMODEL' (a renommer en fonction du modele)
# qui contiendra le modele deja entraine

# remplacer MYMODELINSTANCE par le modele fitte sur les donnees

import pickle

output=file('./sauvegarde_MYMODEL','w')
pickle.dump(MYMODELINSTANCE,output)
output.close()
