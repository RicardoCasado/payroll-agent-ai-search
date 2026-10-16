
The approach used is unit testing with mocking.
The idea is to check if the functions give the desire outputs when it receives a specific inputs


La idea fundamental: no estás comprobando que Azure funciona correctamente. Estás comprobando que tu código calcula correctamente las estadísticas cuando recibe unos datos determinados, independientemente de dónde procedan.

It works with simulate data defined in the function()  payroll_loader
and store here 
``
return_value=pd.DataFrame({ 
        })
``



Esto confirma que tu función calculate_salary_statistics() supera los casos que hemos preparado:
1. Filtrado y normalización de categorías salariales.
2. Categorías vacías.
3. Categorías inexistentes.
4. Columnas ausentes.
5. Salarios inválidos.
6. Errores RuntimeError.
7. Errores ValueError.


## Github Actions

We use Github Actions to implement (CI) continuous integration and execute severals tests to avoid potential issues. As it is a new virtual environment, we need to define the configuration in a file yml. 










