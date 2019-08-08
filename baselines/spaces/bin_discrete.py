from itertools import repeat
import numpy as np
from gym.spaces.space import Space

import numpy as np

from gym.spaces.space import Space

class Bin_Discrete(Space):
    """A binary array of discrete spaces in :math:`\{ 0, 1, \dots, n-1 \}`. 
    
    Example::
    
        >>> Bin_Discrete(198)
        
    """
    def __init__(self, n):
        self.n = n
        #self.arr = (1,n)
        self.arr = (n,)
        super(Bin_Discrete, self).__init__(self.arr, np.int64)

    def sample(self):
        possibles = []
        for i in range(self.n):
            if self.arr[i] == 0:
                possibles.append(i)
        action = random.choice(possibles)
        self.arr[action] = 1
        return self.arr

    def contains(self, x):
        uniques, idxs = np.unique(x, return_index=True)
        if uniques.len == 2 or uniques.len == 1:
            for i in idxs:
                if x[i] != 1 and x[i] != 0:
                    return False
        else: 
            return False
        return True
        

    def __repr__(self):
        return "Bin_Discrete(%d)" % self.n

    def __eq__(self, other):
        return isinstance(other, Bin_Discrete) and self.n == other.n
        
    def to_jsonable(self, sample_n):
        """Convert a batch of samples from this space to a JSONable data type."""
        # By default, assume identity is JSONable
        return sample_n

    def from_jsonable(self, sample_n):
        """Convert a JSONable data type to a batch of samples from this space."""
        # By default, assume identity is JSONable
        return sample_n
        
    def update (actions) :
        self.arr[actions] = 1
