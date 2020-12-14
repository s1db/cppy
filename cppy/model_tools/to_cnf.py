from ..model import *
from ..expressions import *
from ..variables import *
"""
 Do tseitin transform on list of constraints
 Only supports [], and, or, -, -> for now
"""
def to_cnf(constraints):
    # print(constraints)
    # 'constraints' should be list, but lets add some special cases
    if isinstance(constraints, Model):
        # transform model's constraints
        return to_cnf(constraints.constraints)
    if isinstance(constraints, Operator): 
        if constraints.name == "and":
            # and() is same as a list of its elements
            constraints = constraints.args
        elif constraints.name in ['or', '->']:
            # make or() into [or()] as result will be cnf anyway
            constraints = [constraints]
    # print(constraints)
    if isinstance(constraints, Expression):
        # transform expression directly
        return tseitin_transform(constraints)
    if isinstance(constraints, bool):
        return tseitin_transform(constraints)

    if isinstance(constraints, Comparison):
        subcnf = to_cnf( implies(constraints.args[0], constraints.args[1]) & implies(constraints.args[1], constraints.args[0]))
        return subcnf

    cnf = []
    
    for expr in constraints:
        # print("Here")
        # print(expr)
        if isinstance(expr, Operator):
            if expr.name == '->':
                # turn into OR constraint, a -> b =:= ~a | b
                expr.args[0] = ~expr.args[0]
                expr.name = 'or'
                # TODO: perhaps check whether any arg is a disjunction, flatten
            if expr.name == "or":
                # special case: OR constraint, shortcut to disjunction of subexprs
                subvarcnfs = [tseitin_transform(subexpr) for subexpr in expr.args]
                cnf.append( Operator("or", [subv for (subv,_) in subvarcnfs]) )
                cnf += [clause for (_,subcnf) in subvarcnfs for clause in subcnf]
            elif expr.name == "and":
                # special case: AND constraint, flatten into toplevel conjunction
                subcnf = to_cnf(expr.args)
                cnf += subcnf
        elif isinstance(expr, Comparison) and expr.name == '==' and not isinstance(expr.args[1], int):
            # XXX naive implemnetation
            # print(expr)
            # subcnf = to_cnf( implies(expr.args[0], expr.args[1]) & implies(expr.args[1], expr.args[0]))
            # cnf += subcnf
            # XXX smarter one ?
            new_var, new_cnf = tseitin_transform(expr)
            cnf.append(new_var)
            cnf += new_cnf
        # TODO: check whether correct or not especially if expr == False
        elif isinstance(expr, bool):
            continue
        elif isinstance(expr, list):
            # same special case as 'AND': flatten into top-level
            subcnf = to_cnf(expr)
            cnf += subcnf
        else:
            print(expr)
            newvar, newcnf = tseitin_transform(expr)
            cnf.append(newvar)
            cnf += newcnf
    return cnf


def tseitin_transform(expr):
    # base cases
    if isinstance(expr, bool):
        return (expr, [])
    if isinstance(expr, BoolVarImpl):
        return (expr, [])

    # e == 0 and e == 1
    if isinstance(expr, Comparison) and expr.name == '==' and isinstance(expr.args[1], int):
        if expr.args[1] == 1:
            return tseitin_transform(expr.args[0])
        elif expr.args[1] == 0:
            (var,cnf) = tseitin_transform(expr.args[0])
            return (~var, cnf)
        else:
            raise Exception("Tseitin: e == '"+str(expr.args[1])+"' not supported yet")

    # XXX changed here
    if isinstance(expr, Comparison) and expr.name != '==':
        raise Exception("Tseitin: Expression '"+str(expr)+"' not supported yet:", type(expr))

    # XXX changed here disabled 
    # if not isinstance(expr, Operator):
    #     raise Exception("Tseitin: Expression '"+str(expr)+"' not supported yet:", type(expr))

    # Operators:
    implemented = ['-', 'and', 'or', '->', '==']
    if not expr.name in implemented:
        raise Exception("Tseitin: Operator '"+expr.name+"' not implemented")

    # recursively transform the arguments first and merge their cnfs
    subvarcnfs = [tseitin_transform(subexpr) for subexpr in expr.args]
    cnf = [clause for (_,subcnf) in subvarcnfs for clause in subcnf]
    subvars = [subvar for (subvar,_) in subvarcnfs]

    if isinstance(expr, Operator):
        # special case: unary -, negate single argument var
        if expr.name == '-':
            return (~subvars[0], cnf)

    Aux = BoolVarImpl()
    # print(Aux.name + 1)
    if expr.name == "and":
        cnf.append( Operator("or", [Aux] + [~var for var in subvars]) )
        for var in subvars:
            cnf.append( ~Aux | var )

    if expr.name == "or":
        cnf.append( Operator("or", [~Aux] + [var for var in subvars]) )
        for var in subvars:
            cnf.append( Aux | ~var )

    if expr.name  == "->":
        # Implication is treated as if it were "or": A -> B <=> ~A or B
        A = subvars[0]
        B = subvars[1]
        cnf = [(~Aux | ~A | B), (Aux | A), (Aux | ~B)]

    # # XXX changed added ==
    if expr.name == '==':
        # print("here ?")
        # (1) Aux => (A <=> B)
        # (2) ~Aux => (A <=> ~B)
        # cnf= [(~A | B), ( ~B | A)]
        # print(subvars)
        A = subvars[0]
        B = subvars[1]
        cnf = [(~Aux | ~A | B), (~Aux | ~B | A), (Aux | A | B), (Aux | ~A | ~B)]

    return Aux, cnf

